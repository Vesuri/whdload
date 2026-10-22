#!/usr/bin/env python3
"""Drive Formula One Grand Prix in FS-UAE through the Barto gdb stub.

  python3 tools/f1gp.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/f1gp.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
Input goes through the native build's harness: gdb monitor key|mouse|input|fields.
Uses the native arm64 FS-UAE ($FSUAE_ARM) unless FSUAE is set; it profiles the whole
24-bit space without a trigger, so no lldb profiler-window fix.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FSUAE', os.environ.get('FSUAE_ARM')
                      or os.path.expanduser('~/.local/share/amiga/fs-uae-arm/fs-uae'))
server = Server('f1gp', root=ROOT, profile_window=False)

if __name__ == '__main__':
    server.main(sys.argv[1:])
