#!/usr/bin/env python3
"""Drive the original Test Drive II in FS-UAE through the Barto gdb stub.

  python3 tools/td2.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/td2.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve), the emulator left running
after each unless noted: stop | cont, gdb <text>, shot <png>, profile <fields> <bin> (PAL
fields, Barto format), wait <seconds>, until <addr> (stays stopped there), quit. The run
options of common/run.sh (SETUP, TD_SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...) apply to
serve. Run it, and the tools that use its socket, from the game directory.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('td2')
SOCK = server.sock

if __name__ == '__main__':
    server.main(sys.argv[1:])
