#!/usr/bin/env python3
"""Drive Indianapolis 500 in FS-UAE through the Barto gdb stub.

  python3 tools/i500.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/i500.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
The run options of common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve;
SLAVE=original boots the installed v3.0 slave.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('i500')
SOCK = server.sock

if __name__ == '__main__':
    server.main(sys.argv[1:])
