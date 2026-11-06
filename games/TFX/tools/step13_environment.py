"""Separate runtime directories/ports for independent CPU regression sessions.

STEP13_WORKER_ROOT names the session: its last path component becomes the common/run.sh
INSTANCE (its own tmp/run/<instance>/.run, drives and gdb-stub port). STEP13_BUILD, a
directory holding TFX.Slave, selects the slave when PROFILE_SLAVE does not.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402


def prepare(replay):
    original = replay.ROOT
    if not os.environ.get('STEP13_WORKER_ROOT'):
        return original
    worker = Path(os.environ['STEP13_WORKER_ROOT']).resolve()
    worker.mkdir(parents=True, exist_ok=True)
    os.environ['INSTANCE'] = 'step13-' + worker.name
    if os.environ.get('STEP13_BUILD') and not os.environ.get('PROFILE_SLAVE'):
        os.environ['PROFILE_SLAVE'] = str(Path(os.environ['STEP13_BUILD']) / 'TFX.Slave')
    replay.server = game_server('tfx-step13')
    return original
