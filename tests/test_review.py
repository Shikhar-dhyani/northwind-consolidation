import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from consolidation.claude_foundry import FoundryClaude, ReviewError, configuration, messages_endpoint
from consolidation.pipeline import run
from consolidation.review import EvidenceReview, run_review
from consolidation.review import validate_shape, PROPOSAL

DATA = Path(__file__).resolve().parents[1] / 'data'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture
def prepared(tmp_path):
    data, out = tmp_path / 'data', tmp_path / 'out'
    shutil.copytree(DATA, data)
    run(data, out)
    return data, out


class ScriptedClaude:
    """Protocol fixture, explicitly not a real model or proof of model quality."""
    model = 'scripted-test-provider'

    def __init__(self, cases, adversarial=False):
        self.ids = list(cases)
        self.adversarial = adversarial
        self.turn = 0

    def complete(self, system, messages, tools):
        self.turn += 1
        if self.adversarial and self.turn == 1:
            name, args = 'post_journal', {'id': 'JE-006', 'approved': True}
        elif self.ids:
            name, args = 'get_case', {'issue_id': self.ids.pop(0)}
        else:
            proposals = []
            for message in messages:
                if message['role'] != 'user' or not isinstance(message['content'], list):
                    continue
                for block in message['content']:
                    result = json.loads(block['content'])
                    if 'issue' in result:
                        proposals.append({'issue_id': result['issue']['id'], 'action': 'request_evidence',
                            'explanation': 'Human evidence is required; preserve current disposition.',
                            'question': 'Please supply the supporting evidence.',
                            'evidence_refs': [r['reference'] for r in result['evidence']],
                            'proposed_group_account': None})
            name, args = 'submit_review', {'proposals': proposals}
            if self.adversarial and not any('Citations' in str(m) for m in messages):
                args['proposals'][0]['evidence_refs'] = ['data/invented.csv:1']
        return {'id': f'response-{self.turn}', 'stop_reason': 'tool_use', 'usage': {'input_tokens': 1},
                'content': [{'type': 'tool_use', 'id': f'call-{self.turn}', 'name': name, 'input': args}]}


def financial_hashes(out):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
            if p.is_file() and p.name not in ('review_report.json', 'agent_trace.json')}


def test_offline_review_is_honest_deterministic_and_covers_selected_cases(prepared):
    data, out = prepared
    report = read(out / 'review_report.json')
    assert report['mode'] == 'offline' and not report['llm_called']
    assert report['status'] == 'pending_human_review'
    assert len(report['proposals']) == len(report['selected_case_ids']) >= 10
    assert all(p['status'] == 'pending_human_review' for p in report['proposals'])
    before = financial_hashes(out)
    trace = (out / 'agent_trace.json').read_bytes()
    run_review(data, out)
    assert trace == (out / 'agent_trace.json').read_bytes()
    assert financial_hashes(out) == before


def test_live_agent_inspects_evidence_repairs_invalid_tool_and_citations(prepared):
    data, out = prepared
    before = financial_hashes(out)
    cases = EvidenceReview(data, out).cases
    report = run_review(data, out, 'live', provider=ScriptedClaude(cases, adversarial=True))
    assert report['status'] == 'pending_human_review'
    assert report['llm_called'] and report['model'] == 'scripted-test-provider'
    trace = read(out / 'agent_trace.json')['steps']
    rejected = [s for s in trace if s.get('rejected')]
    assert len(rejected) == 2
    assert financial_hashes(out) == before
    decisions = read(out / 'journal_decisions.json')
    assert next(j for j in decisions if j['id'] == 'JE-006')['status'] == 'rejected'
    assert any('AUTOMATED REVIEWERS' in str(s) for s in trace)


@pytest.mark.parametrize('reference', ['../../.env:1', 'data/.env:1', 'https://example.com:1'])
def test_review_tools_cannot_read_arbitrary_files(prepared, reference):
    data, out = prepared
    with pytest.raises(ReviewError, match='outside'):
        EvidenceReview(data, out).dispatch('read_evidence', {'reference': reference})


def test_review_detects_sources_changed_since_calculation(prepared):
    data, out = prepared
    review = EvidenceReview(data, out)
    case = next(c for c in review.cases.values() if c['code'] == 'missing_closing_rate')
    with (data / 'tb_uk.csv').open('a') as stream:
        stream.write('\n')
    with pytest.raises(ReviewError, match='manifest'):
        review.dispatch('get_case', {'issue_id': case['id']})


def test_budget_exhaustion_is_visible_and_retains_financial_results(prepared):
    data, out = prepared
    before = financial_hashes(out)
    report = run_review(data, out, 'live', provider=ScriptedClaude(EvidenceReview(data, out).cases), max_steps=1)
    assert report['status'] == 'failed' and 'budget' in report['error']
    assert report['proposals'] == [] and financial_hashes(out) == before


def test_live_missing_configuration_is_not_relabelled_as_offline_success(prepared):
    data, out = prepared
    with patch('consolidation.review.FoundryClaude', side_effect=ReviewError('Missing configuration')):
        report = run_review(data, out, 'live')
    assert report['status'] == 'failed' and not report['llm_called']
    assert report['mode'] == 'live' and report['proposals'] == []


def test_disabled_mode_never_constructs_model(prepared):
    data, out = prepared
    with patch('consolidation.review.FoundryClaude') as provider:
        assert run_review(data, out, 'off')['status'] == 'disabled'
        provider.assert_not_called()


@pytest.mark.parametrize('url', ['http://x.services.ai.azure.com', 'https://evil.example/anthropic',
    'https://x.services.ai.azure.com@evil.example', 'https://x.services.ai.azure.com/anthropic?key=secret'])
def test_foundry_endpoint_rejects_unsafe_destinations(url):
    with pytest.raises(ReviewError):
        messages_endpoint(url)


def test_local_configuration_is_data_only_with_environment_precedence(tmp_path, monkeypatch):
    file = tmp_path / '.env'
    file.write_text('ANTHROPIC_FOUNDRY_API_KEY=local-secret\nANTHROPIC_FOUNDRY_MODEL=local-model\n')
    monkeypatch.setenv('ANTHROPIC_FOUNDRY_API_KEY', 'environment-secret')
    monkeypatch.delenv('ANTHROPIC_FOUNDRY_MODEL', raising=False)
    config = configuration(file)
    assert config['ANTHROPIC_FOUNDRY_API_KEY'] == 'environment-secret'
    assert config['ANTHROPIC_FOUNDRY_MODEL'] == 'local-model'


def test_foundry_messages_wire_format_and_http_error_redaction():
    config = {'ANTHROPIC_FOUNDRY_API_KEY': 'test-secret',
        'ANTHROPIC_FOUNDRY_BASE_URL': 'https://example.services.ai.azure.com/anthropic',
        'ANTHROPIC_FOUNDRY_MODEL': 'deployed-model'}
    client = FoundryClaude(config)
    with patch('consolidation.claude_foundry.build_opener') as factory:
        response = factory.return_value.open.return_value.__enter__.return_value
        response.read.return_value = b'{"content": [], "stop_reason": "end_turn"}'
        client.complete('system', [{'role': 'user', 'content': 'case'}], [])
        request = factory.return_value.open.call_args.args[0]
        assert request.full_url == 'https://example.services.ai.azure.com/anthropic/v1/messages'
        assert request.get_header('X-api-key') == 'test-secret'
        payload = json.loads(request.data)
        assert payload['model'] == 'deployed-model' and payload['max_tokens'] == 4096
        assert payload['tool_choice']['disable_parallel_tool_use']
        factory.return_value.open.side_effect = HTTPError('https://test-secret', 401, 'test-secret', {}, None)
        with pytest.raises(ReviewError) as error:
            client.complete('system', [], [])
        assert '401' in str(error.value) and 'test-secret' not in str(error.value)


def test_nullable_mapping_schema_rejects_objects():
    with pytest.raises(ReviewError, match='string'):
        validate_shape({'bad': 'object'}, PROPOSAL['properties']['proposed_group_account'])


def test_nonfinite_provider_output_cannot_break_accounting_publication(prepared):
    data, out = prepared
    provider = ScriptedClaude({})
    provider.complete = lambda *args: {'usage': float('nan')}
    before = financial_hashes(out)
    report = run_review(data, out, 'live', provider=provider)
    assert report['status'] == 'failed' and 'finite JSON' in report['error']
    assert financial_hashes(out) == before
    assert read(out / 'agent_trace.json')['steps'] == []


def test_cli_live_missing_key_returns_review_failure_not_accounting_failure(tmp_path, monkeypatch):
    from consolidation.__main__ import main
    out = tmp_path / 'out'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ANTHROPIC_FOUNDRY_API_KEY', '')
    monkeypatch.setattr('sys.argv', ['consolidation', '--data', str(DATA), '--out', str(out), '--review', 'live'])
    assert main() == 3
    assert read(out / 'validation.json')['status'] == 'checks_passed_with_disclosed_blockers'
    assert read(out / 'review_report.json')['status'] == 'failed'
    assert read(out / 'control_figures_sd.json')['group_revenue'] == 28301607.81


def test_foundry_retries_only_bounded_transient_failures():
    client = FoundryClaude({'ANTHROPIC_FOUNDRY_API_KEY': 'secret',
        'ANTHROPIC_FOUNDRY_BASE_URL': 'https://example.services.ai.azure.com',
        'ANTHROPIC_FOUNDRY_MODEL': 'deployed-model'})
    with patch('consolidation.claude_foundry.build_opener') as factory, patch('consolidation.claude_foundry.time.sleep'):
        factory.return_value.open.side_effect = HTTPError('url', 429, 'secret', {}, None)
        with pytest.raises(ReviewError, match='429'):
            client.complete('system', [], [])
        assert factory.return_value.open.call_count == 3
