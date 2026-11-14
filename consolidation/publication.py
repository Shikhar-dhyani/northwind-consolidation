"""Publish complete generated directories without exposing partly written files."""

from pathlib import Path
import shutil
import time
from tempfile import TemporaryDirectory

from .model import InputError


def check_destination(out):
    if out.is_symlink() or (hasattr(out, 'is_junction') and out.is_junction()):
        raise InputError('Output cannot be a link or junction')
    if out.exists() and (not out.is_dir() or (any(out.iterdir()) and not all(
            (out / name).is_file() for name in ('control_figures_sd.json', 'validation.json', 'input_manifest.json')))):
        raise InputError('Nonempty output is not a recognized generated consolidation directory')


def rename(source, target):
    # Windows indexers/virus scanners can temporarily deny directory renames.
    for attempt in range(5):
        try:
            source.rename(target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.05 * 2 ** attempt)


def publish(staged: Path, out: Path, workspace: Path):
    # These exact resolved targets are siblings under the explicitly selected
    # output parent. The backup is owned by this temporary publication workspace.
    backup = workspace / 'previous'
    if workspace.resolve().parent != out.parent.resolve() or staged.resolve().parent != workspace.resolve():
        raise InputError('Publication paths escaped their output workspace')
    if out.exists():
        rename(out, backup)
    try:
        rename(staged, out)
    except Exception:
        if backup.exists() and not out.exists():
            rename(backup, out)
        raise


def execute(data, out, audit, calculate, fail):
    check_destination(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=f'.{out.name}-publish-', dir=out.parent) as temp:
        workspace = Path(temp)
        stage = workspace / 'results'
        stage.mkdir()
        try:
            result = calculate(data, stage, audit)
            # PDFs are separately source-hashed by the packager. Archives are
            # regenerated, rather than carrying old financial results forward.
            if (out / 'pdf').is_dir():
                shutil.copytree(out / 'pdf', stage / 'pdf', symlinks=True)
            publish(stage, out, workspace)
            return result
        except Exception as exc:
            failed = workspace / 'failure'
            failed.mkdir()
            fail(failed, audit, exc)
            try:
                publish(failed, out, workspace)
            except OSError as publication_error:
                # A persistent directory lock must not leave old figures labelled
                # valid if individual result files can still be overwritten.
                fail(out, audit, publication_error)
            raise InputError(str(exc), getattr(exc, 'refs', ())) from exc
