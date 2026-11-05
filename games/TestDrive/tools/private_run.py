"""A capture's own emulator: a common/run.sh instance named after its output directory.

    from private_run import private_server
    s = private_server('roadshift', out)    # out: a fresh directory under tmp/
    g = s.boot(env)

The instance runs in tmp/run/<instance>/.run, so it never touches the default instance or
another capture; out/.run links to it, where the captures read machine.json, fsuae.log and
the drives.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from game_server import game_server  # noqa: E402


def private_server(name, out):
    out = Path(out).resolve()
    instance = re.sub(r'[^A-Za-z0-9_-]+', '-', str(out.relative_to(ROOT / 'tmp'))).strip('-')
    os.environ['INSTANCE'] = instance
    server = game_server(name, profile_window=False)
    run = ROOT / 'tmp/run' / instance / '.run'
    run.mkdir(parents=True, exist_ok=True)
    link = out / '.run'
    if not link.is_symlink():
        link.symlink_to(os.path.relpath(run, out))
    return server
