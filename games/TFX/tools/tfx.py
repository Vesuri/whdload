#!/usr/bin/env python3
"""TFX harness server: boot common/run.sh under the Barto gdb stub and take commands.

  python3 tools/tfx.py serve        boot (DEBUG=1) and listen
  python3 tools/tfx.py shot F.png   screenshot of the next field
  python3 tools/tfx.py wait 10      let it run
  python3 tools/tfx.py quit         stop gdb and the emulator

The run options of common/run.sh and game.sh (SETUP, SLAVE, WHD_ARGS, FPSP040, FPSP060,
HDF, RUN_CMD, INSTANCE, ...) apply to serve through the environment.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('tfx')
ROOT = server.root

if __name__ == '__main__':
    server.main(sys.argv[1:])
