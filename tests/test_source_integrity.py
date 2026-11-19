"""Protect the unmodified bundle, including original line endings."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_original_input_bytes():
    manifest = json.loads((ROOT / 'assignment/input_sha256.json').read_text())
    for relative, expected in manifest.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for metadata in (ROOT / 'transcripts/runtime_claude').glob('*/PROVENANCE.json'):
        for name, expected in json.loads(metadata.read_text(encoding='utf-8'))['files'].items():
            assert hashlib.sha256((metadata.parent / name).read_bytes()).hexdigest() == expected
