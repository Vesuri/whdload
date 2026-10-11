#!/usr/bin/env python3
"""Drive the original Stellar 7 in FS-UAE through the Barto gdb stub.

  python3 tools/stellar7.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/stellar7.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, until <addr>, quit.
"""
import os, subprocess, sys
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.gdbserve import BASETEXT_VM, Server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, 'amiga/.run')
SOCK = os.path.join(RUN, 'stellar7.sock')

# The stub's profiler PC window (amigaxdev.gdbserve, BASETEXT_VM), set in one lldb attach.
LLDB_FIX = (
    'script t=lldb.debugger.GetSelectedTarget(); h=t.GetModuleAtIndex(0).GetObjectFileHeaderAddress(); '
    'a=h.GetLoadAddress(t)-h.GetFileAddress()+%d; e=lldb.SBError(); p=t.GetProcess(); '
    'p.WriteMemory(a, (0).to_bytes(4,"little")+(0x7fffffff).to_bytes(4,"little"), e); '
    'print("WINDOW", p.ReadMemory(a, 8, e).hex())')


def fix_profile_window(server):
    # One attach that computes the slide and writes the window: each lldb attach to this
    # x86_64 (Rosetta) process costs ~40 s, so the earlier image-list-then-write pair could
    # exceed a 60 s timeout.
    pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
    out = subprocess.run(['lldb', '-p', pid, '--batch', '-o', LLDB_FIX % BASETEXT_VM],
                         capture_output=True, text=True, timeout=300).stdout
    assert 'WINDOW 00000000ffffff7f' in out, out


server = Server('stellar7', root=ROOT, profile_window=fix_profile_window)

if __name__ == '__main__':
    server.main(sys.argv[1:])
