import json
import shutil
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import pytest

from consolidation.model import InputError
from consolidation.pipeline import run
from tests.test_pipeline import mutate_csv, add_sgd_rate, read_json

DATA = Path(__file__).resolve().parents[1] / 'data'


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / 'data'
    shutil.copytree(DATA, folder)
    return folder


def journals(bundle, mutate):
    path = bundle / 'adjustments.json'
    batch = json.loads(path.read_text())
    mutate(batch)
    path.write_text(json.dumps(batch))


@pytest.mark.parametrize('change', ['lines_null', 'entries_null', 'empty_lines'])
def test_malformed_journals_replace_all_old_results(bundle, tmp_path, change):
    out = tmp_path / 'out'
    run(bundle, out)
    (out / 'obsolete.txt').write_text('stale')
    def mutate(batch):
        if change == 'entries_null':
            batch['entries'] = None
        else:
            batch['entries'][0]['lines'] = None if change == 'lines_null' else []
    journals(bundle, mutate)
    with pytest.raises(InputError):
        run(bundle, out)
    assert not (out / 'obsolete.txt').exists()
    assert all(v is None for v in read_json(out / 'control_figures_sd.json').values())
    assert read_json(out / 'validation.json')['status'] == 'failed'


def test_unexpected_error_after_partial_staging_never_publishes_partial_files(bundle, tmp_path):
    out = tmp_path / 'out'
    run(bundle, out)
    def broken_emit(stage, *args):
        (stage / 'incomplete.json').write_text('{')
        raise TypeError('simulated unexpected serialization failure')
    with patch('consolidation.pipeline.emit', broken_emit), pytest.raises(InputError):
        run(bundle, out)
    assert not (out / 'incomplete.json').exists()
    assert read_json(out / 'validation.json')['status'] == 'failed'


def test_publication_refuses_to_clear_unrelated_directory(bundle, tmp_path):
    out = tmp_path / 'user-files'
    out.mkdir()
    note = out / 'notes.txt'
    note.write_text('keep')
    with pytest.raises(InputError, match='not a recognized'):
        run(bundle, out)
    assert note.read_text() == 'keep'
