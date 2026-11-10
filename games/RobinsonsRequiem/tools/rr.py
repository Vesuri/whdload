#!/usr/bin/env python3
"""The gdb-stub game server (common/tools/game_server.py).

    python3 tools/rr.py serve        boot (common/run.sh with DEBUG=1), attach gdb, listen
    python3 tools/rr.py wait 30      let it run
    python3 tools/rr.py shot x.png   screenshot of the next field
    python3 tools/rr.py quit         stop gdb and the emulator

The run options of common/run.sh apply to serve through the environment (VARIANT=
RobinsonsRequiemAGA, SLAVE=original, SETUP=a1200-030, WARP=1 WINDOW=none, ...).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('rr')

if __name__ == '__main__':
    server.main(sys.argv[1:])
