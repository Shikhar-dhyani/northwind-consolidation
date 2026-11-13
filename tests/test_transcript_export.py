import json

from scripts.export_transcript import export


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
