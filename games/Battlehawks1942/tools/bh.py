#!/usr/bin/env python3
"""Drive the original Battlehawks 1942 in FS-UAE through the Barto gdb stub.

  python3 tools/bh.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/bh.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
The run options of common/run.sh (SETUP, SLAVE, BUILD, WHD_ARGS, INSTANCE, ...) apply to serve.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
server = game_server('bh')
SOCK = server.sock

if __name__ == '__main__':
    server.main(sys.argv[1:])
