import shutil

from tox import reporter


def ensure_empty_dir(path):
    if path.check():
        reporter.info(f"  removing {path}")
        shutil.rmtree(str(path), ignore_errors=True)
        path.ensure(dir=1)
