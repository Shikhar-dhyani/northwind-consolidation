import shutil
from pathlib import Path

import pytest

from consolidation.inputs import Inputs
from consolidation.model import Audit, InputError

DATA = Path(__file__).resolve().parents[1] / 'data'


@pytest.mark.parametrize('filename', ['entities.csv', 'group_coa.csv'])
def test_duplicate_metadata_is_blocked(tmp_path, filename):
    target = tmp_path / 'data'
    shutil.copytree(DATA, target)
    path = target / filename
    lines = path.read_text().splitlines()
    path.write_text('\n'.join(lines + [lines[1]]) + '\n')
    with pytest.raises(InputError, match='[Dd]uplicate'):
        Inputs(target, Audit()).load()
