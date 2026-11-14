import json

from scripts.export_transcript import export, redact, redact_discovery


def test_export_preserves_failed_tool_record_and_omits_private_records(tmp_path):
    source, target = tmp_path / 'session.jsonl', tmp_path / 'export/transcript.jsonl'
    records = [
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer', 'content': 'internal'}},
        {'type': 'response_item', 'payload': {'type': 'reasoning', 'summary': 'private'}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': 'Run tests. candidate@example.test'}},
        {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'output': 'FAILED: DID NOT RAISE'}},
    ]
    source.write_text(''.join(json.dumps(record) + '\n' for record in records))
    export(source, target)
    result = [json.loads(line)['payload'] for line in target.read_text().splitlines()]
    assert len(result) == 2
    assert result[0]['content'] == 'Run tests. [REDACTED EMAIL]'
    assert result[1]['output'] == 'FAILED: DID NOT RAISE'
    assert 'private' not in target.read_text()


def test_completion_comes_from_actual_session_events(tmp_path):
    source, target = tmp_path / 'session.jsonl', tmp_path / 'export/transcript.jsonl'
    records = [{'type': 'event_msg', 'payload': {'type': 'task_started'}},
               {'type': 'event_msg', 'payload': {'type': 'task_complete'}}]
    source.write_text(''.join(json.dumps(record) + '\n' for record in records))
    status = export(source, target)
    assert status['current_session_complete']
    assert status['completed_turns'] == 1
    records.append({'type': 'event_msg', 'payload': {'type': 'task_started'}})
    source.write_text(''.join(json.dumps(record) + '\n' for record in records))
    assert not export(source, target)['current_session_complete']


def test_pasted_claude_record_is_preserved_verbatim(tmp_path):
    source, target = tmp_path / 'session.jsonl', tmp_path / 'export/transcript.jsonl'
    answer = 'claude , and here is the orignal conversation :-\nOriginal text.\n\n  Keep spacing.\n'
    text = '<send_user_message_question_reply>\n' + json.dumps([{'answer': answer}]) + '\n</send_user_message_question_reply>'
    record = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
              'content': [{'type': 'input_text', 'text': text}]}}
    source.write_text(json.dumps(record) + '\n')
    status = export(source, target)
    assert (target.parent / 'claude-planning.txt').read_bytes() == answer.encode('utf-8')
    assert status['earlier_planning_sessions_available']


def test_private_discovery_metadata_is_redacted_at_multiple_json_depths():
    raw = json.dumps({'threads': [{'id': 'preserved', 'kind': 'codex', 'title': 'Private title',
        'summary': 'Private work with "quoted", text and trailing \\'}]})
    for depth in range(4):
        cleaned = redact_discovery(raw)
        assert 'Private title' not in cleaned
        assert 'Private work' not in cleaned
        assert 'preserved' in cleaned
        decoded = cleaned
        for _ in range(depth + 1):
            decoded = json.loads(decoded)
        assert decoded['threads'][0]['summary'] == '[REDACTED PRIVATE CHAT METADATA]'
        raw = json.dumps(raw)


def test_nonpersonal_financial_summary_and_ai_mistake_are_preserved():
    raw = '{"summary":"JE-006 was wrongly accepted in this draft", "title":"Financial draft"}'
    assert redact(raw) == raw


def test_only_identified_discovery_results_redact_private_chat_fields(tmp_path):
    source, target = tmp_path / 'session.jsonl', tmp_path / 'out/transcript.jsonl'
    discovery = json.dumps({'threads': [{'id': 'unrelated', 'kind': 'chatgpt', 'title': 'Private work'}],
                            'summary': 'Preserve this ordinary summary'})
    rows = [
        {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'one',
            'name': 'exec', 'input': 'await tools.mcp__codex_app__list_threads({});'}},
        {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'one', 'output': discovery}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
            'content': [{'type': 'output_text', 'text': '{"summary":"An AI mistake"}'}]}},
    ]
    source.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    export(source, target)
    result = target.read_text()
    assert 'Private work' not in result
    assert 'Preserve this ordinary summary' in result
    assert 'An AI mistake' in result
