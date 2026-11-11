#!/usr/bin/env python3
"""Drive Buggy Boy in FS-UAE through the gdb stub (common/tools/game_server.py).

  python3 tools/buggyboy.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/buggyboy.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <s>, until <addr>, quit. The run options of
common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, WARP, WINDOW, ...) apply to serve.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('bug')

if __name__ == '__main__':
    server.main(sys.argv[1:])
