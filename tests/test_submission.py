import hashlib
import json

import pytest

from scripts.prepare_submission import transcript_bytes


@pytest.mark.parametrize('change', ['none', 'modified_excerpt', 'missing_excerpt'])
def test_packager_verifies_both_claude_source_records(tmp_path, change):
    def record(name, text):
        path = tmp_path / name
        path.write_bytes(text.encode('utf-8'))
        return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    initial = record('initial.txt', 'Original initial text')
    excerpt = record('excerpts.jsonl', 'Original later text')
    (tmp_path / 'SESSIONS.json').write_text(json.dumps({'sessions': [initial]}))
    (tmp_path / 'CLAUDE_REVIEW_PROVENANCE.json').write_text(json.dumps(excerpt))
    runtime = tmp_path / 'runtime_claude/01_live'
    runtime.mkdir(parents=True)
    (runtime / 'agent_trace.json').write_bytes(b'Original runtime trace')
    (runtime / 'PROVENANCE.json').write_text(json.dumps({'files': {
        'agent_trace.json': hashlib.sha256((runtime / 'agent_trace.json').read_bytes()).hexdigest()}}))
    if change == 'none':
        transcript_bytes(tmp_path)
        (runtime / 'agent_trace.json').write_bytes(b'Modified runtime trace')
        with pytest.raises(RuntimeError, match='Transcript checksum mismatch'):
            transcript_bytes(tmp_path)
    else:
        path = tmp_path / excerpt['path']
        if change == 'modified_excerpt':
            path.write_text('Changed later text')
        else:
            path.unlink()
        with pytest.raises(RuntimeError, match='Transcript'):
            transcript_bytes(tmp_path)
