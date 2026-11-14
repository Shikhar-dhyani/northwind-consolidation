"""Validate and package committed source, results, documents and complete Git history.

Requires test dependencies. Optional PDFs must first be rendered with
scripts/render_submission_pdfs.py and requirements-docs.txt.
No email is sent and no remote repository is changed by this script.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from consolidation.pipeline import run
from consolidation.reporting import CONTROL_KEYS, rounded

FINANCIAL_FILES = ('consolidated_tb.csv', 'balance_sheet.json', 'profit_and_loss.json',
    'changes_in_equity.json', 'eliminations.csv', 'issues.json', 'control_figures_sd.json',
    'control_explanations.json', 'journal_decisions.json', 'ledger_postings.csv',
    'validation.json', 'input_manifest.json', 'scenarios/alternative_disclosed_assumptions.json')


def command(*args):
    result = subprocess.run(args, cwd=ROOT, check=False, text=True, encoding='utf-8',
                            errors='replace', capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def original_bytes():
    manifest = json.loads((ROOT / 'assignment/input_sha256.json').read_text())
    for name, expected in manifest.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Original source bytes changed: {name}')


def transcript_bytes(folder):
    registry = json.loads((folder / 'SESSIONS.json').read_text(encoding='utf-8'))
    records = list(registry['sessions'])
    # The later excerpts have their own provenance record, in addition to the
    # original planning text indexed by SESSIONS.json.
    records.append(json.loads((folder / 'CLAUDE_REVIEW_PROVENANCE.json').read_text(encoding='utf-8')))
    for record in records:
        path = (folder / record['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            raise RuntimeError('Transcript file missing or outside transcript directory')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record['sha256']:
            raise RuntimeError(f'Transcript checksum mismatch: {record["path"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-pdfs', action='store_true')
    args = parser.parse_args()
    if command('git', 'status', '--porcelain'):
        raise RuntimeError('Commit the reviewed project changes before packaging; working tree must be clean.')
    original_bytes()
    test_result = command(sys.executable, '-m', 'pytest', '-q')
    print(test_result)
    controls = run(ROOT / 'data', ROOT / 'output')
    if tuple(controls) != CONTROL_KEYS:
        raise RuntimeError('Control-key contract changed')
    validation = json.loads((ROOT / 'output/validation.json').read_text())
    if not all(check['passed'] for check in validation['checks']):
        raise RuntimeError('Runtime control failed')
    coverage = json.loads((ROOT / 'transcripts/EXPORT_STATUS.json').read_text())
    if not coverage['earlier_planning_sessions_available']:
        raise RuntimeError('Earlier planning-session record is missing')
    transcript_bytes(ROOT / 'transcripts')
    docs = []
    pdf_dir = ROOT / 'output/pdf'
    if (pdf_dir / 'pdf_manifest.json').exists():
        manifest = json.loads((pdf_dir / 'pdf_manifest.json').read_text())
        for item in manifest['documents']:
            path = pdf_dir / item['file']
            if hashlib.sha256((ROOT / item['source']).read_bytes()).hexdigest() != item['source_sha256']:
                raise RuntimeError('PDF source changed; rerender documents')
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise RuntimeError('PDF checksum mismatch; rerender documents')
            docs.append(path)
        docs.append(pdf_dir / 'pdf_manifest.json')
    elif args.require_pdfs:
        raise RuntimeError('Render the optional PDF attachments first')
    out = ROOT / 'output/submission'
    out.mkdir(parents=True, exist_ok=True)
    bundle = out / 'northwind-consolidation.bundle'
    command('git', 'bundle', 'create', str(bundle), '--all')
    command('git', 'bundle', 'verify', str(bundle))
    commit = command('git', 'rev-parse', 'HEAD')
    report = {'bundle_id': 'NWG-D0BC', 'git_commit': commit, 'working_tree_clean': True,
        'tests': test_result, 'runtime_controls_passed': len(validation['checks']),
        'controls': rounded(controls), 'blocked_control_keys': [key for key, value in controls.items() if value is None],
        'transcript_coverage': coverage, 'git_history': bundle.name,
        'pdf_attachments': [p.name for p in docs if p.suffix == '.pdf'],
        'email_status': 'Draft prepared; no email sent',
        'financial_status': 'partial_blocked as disclosed; missing inputs are not estimated'}
    report_path = out / 'BUILD_REPORT.json'
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    archive = out / 'northwind-consolidation-NWG-D0BC.zip'
    tracked = command('git', 'ls-files', '-z').split('\0')
    payload = [(ROOT / name, 'northwind-consolidation/' + name) for name in tracked if name]
    payload.extend((ROOT / 'output' / name, 'northwind-consolidation/output/' + name) for name in FINANCIAL_FILES)
    payload.extend((path, 'northwind-consolidation/output/pdf/' + path.name) for path in docs)
    payload.extend([(bundle, bundle.name), (report_path, report_path.name)])
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as zipped:
        for path, name in sorted(payload, key=lambda pair: pair[1]):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            zipped.writestr(info, path.read_bytes())
    with ZipFile(archive) as zipped:
        bad = zipped.testzip()
        if bad:
            raise RuntimeError(f'Archive integrity failure: {bad}')
    print(f'Created {archive}')
    print('Full history is in the verified Git bundle. See BUILD_REPORT.json for status and transcript boundary.')


if __name__ == '__main__':
    main()
