#!/usr/bin/env python3
"""The gdb-stub game server (common/tools/game_server.py).

    python3 tools/game.py serve        boot (common/run.sh with DEBUG=1), attach gdb, listen
    python3 tools/game.py shot x.png   one command to the running server

The run options of common/run.sh apply through the environment (SLAVE=original, BUILD=fast,
WHD_ARGS='CUSTOM2=1', CPU=68020 FAST_KB=4096, ...). The captures and checks use tools/run.sh.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('ff1', profile_window=False)
if __name__ == '__main__':
    server.main(sys.argv[1:])
