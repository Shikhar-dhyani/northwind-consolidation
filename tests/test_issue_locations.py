from pathlib import Path

from consolidation.pipeline import run
import json


def test_issue_primary_locations_point_to_the_problem(tmp_path):
    run(Path(__file__).resolve().parents[1] / 'data', tmp_path / 'output')
    issues = json.loads((tmp_path / 'output/issues.json').read_text())
    mapping = next(i for i in issues if i['code'] == 'mapping_classification')
    assert mapping['amount_affected'] == 180000
    assert 'data/tb_uk.csv:12' in mapping['sources']
    mismatches = [i for i in issues if i['code'] == 'subledger_mismatch']
    assert [(i['file'], i['line']) for i in mismatches] == [
        ('data/subledger_controls.csv', 4), ('data/subledger_controls.csv', 5)]
    missing = next(i for i in issues if i['code'] == 'missing_closing_rate')
    assert (missing['file'], missing['line']) == ('data/tb_uk.csv', 3)
    transit = next(i for i in issues if i['code'] == 'invoice_in_transit')
    assert (transit['file'], transit['line']) == ('data/intercompany.csv', 6)
