#!/usr/bin/env python3
"""Drive the original Test Drive II in FS-UAE through the Barto gdb stub.

  python3 tools/td2.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/td2.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve), the emulator left running
after each unless noted: stop | cont, gdb <text>, shot <png>, profile <fields> <bin> (PAL
fields, Barto format), wait <seconds>, until <addr> (stays stopped there), quit.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
server = Server('td2', root=ROOT)

if __name__ == '__main__':
    server.main(sys.argv[1:])
