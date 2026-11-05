#!/usr/bin/env python3
"""Drive Grand Prix Circuit in FS-UAE through the Barto gdb stub.

  python3 tools/gpc.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/gpc.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
The run options of common/run.sh (SETUP, CPU, CHIP_KB, SLAVE, WHD_ARGS, INSTANCE, ...) apply
to serve. Without SLAVE it boots the shipped slave (SLAVE=original), as the harness always
did; SLAVE=path boots a build. The working directory is the game directory, so gdb memory
dumps can use relative paths under tmp/.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if not os.environ.get('SLAVE'):
    os.environ['SLAVE'] = 'original'
server = game_server('gpc')

if __name__ == '__main__':
    server.main(sys.argv[1:])
