#!/usr/bin/env python3
"""Drive the original Mercenary 3 in FS-UAE through the Barto gdb stub.

  python3 tools/merc3.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/merc3.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
Use the native build (FSUAE="$FSUAE_ARM"): it profiles the whole address space without the
lldb window fix and takes input through `gdb monitor key|mouse|input|fields`.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
server = Server('merc3', root=ROOT,
                profile_window=not os.environ.get('FSUAE', '').endswith('fs-uae-arm/fs-uae'))

if __name__ == '__main__':
    server.main(sys.argv[1:])
