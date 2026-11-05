#!/usr/bin/env python3
"""Drive the original Legends of Valour in FS-UAE through the Barto gdb stub.

  python3 tools/lov.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/lov.py <command...>   send one command to the running server, print the reply

Commands (the emulator is left running after each unless noted):
  stop | cont                  halt / resume the CPU
  gdb <text>                   raw gdb CLI command (halts first, resumes after)
  shot <png>                   record one field, save its screenshot
  profile <fields> <bin>       cycle-exact trace of <fields> PAL fields (Barto format)
  wait <seconds>               let it run
  until <addr>                 run to a breakpoint at addr and stay stopped there
  quit                         kill gdb and the emulator

The run options of common/run.sh (SETUP, SLAVE, BUILD, WHD_ARGS, TAPE, ...) apply to serve
through the environment. The server runs as INSTANCE=cap unless INSTANCE is set, so captures
never stop an interactive `make run` (tmp/run/default/).
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev
from amigaxdev.gdbserve import Server
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import COMMON  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['GAME'] = os.path.basename(ROOT)
# Captures run in their own instance, tmp/run/cap/, apart from interactive sessions in
# tmp/run/default/: run.sh stops only the emulator its instance last started.
INSTANCE = os.environ['INSTANCE'] = os.environ.get('INSTANCE') or 'cap'
RUN_DIR = os.path.join('tmp/run', INSTANCE, '.run')
RUN = os.path.join(ROOT, RUN_DIR)
SOCK = os.path.join(RUN, 'lov.sock')
# gdb runs in the game directory and cannot quote file names, so dump paths are given
# relative to it (SCRATCH).
SCRATCH = 'tmp/scratch'


# The x86_64 stub's profiler window (amigaxdev.gdbserve), fixed in one batch lldb attach.
BASETEXT_VM = int(os.environ.get("BASETEXT_VM", "0x32dea04"), 0)


LLDB_FIX = (
    'script t=lldb.debugger.GetSelectedTarget(); h=t.GetModuleAtIndex(0).GetObjectFileHeaderAddress(); '
    'a=h.GetLoadAddress(t)-h.GetFileAddress()+%d; e=lldb.SBError(); p=t.GetProcess(); '
    'p.WriteMemory(a, (0).to_bytes(4,"little")+(0x7fffffff).to_bytes(4,"little"), e); '
    'print("WINDOW", p.ReadMemory(a, 8, e).hex())')


def fix_profile_window():
    # One attach that computes the slide and writes the window (Indianapolis 500's fix): each
    # lldb attach to this x86_64 (Rosetta) process can take ~40 s.
    pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
    out = subprocess.run(['lldb', '-p', pid, '--batch', '-o', LLDB_FIX % BASETEXT_VM],
                         capture_output=True, text=True, timeout=300).stdout
    assert 'WINDOW 00000000ffffff7f' in out, out


class Lov(Server):
    def boot(self, env=None):
        os.makedirs(os.path.join(ROOT, SCRATCH), exist_ok=True)
        here = os.getcwd()
        os.chdir(ROOT)  # gdb inherits it
        try:
            g = super().boot(env)
        finally:
            os.chdir(here)
        g.profiler_pc_base = None
        return g

    def capture(self, g, fields, target):
        was = g.running; g.stop()
        if os.environ.get('PROFILE_WINDOW') == 'guest':
            assert g.profiler_pc_base == 0x1018, 'guest profiler handshake was not acknowledged'
        else:
            fix_profile_window()
            g.profiler_pc_base = 0
        out = g.cmd(f'monitor profile {fields} "" "{target}"', timeout=1800)
        Path(target).with_suffix('.pc-base').write_text(f'{g.profiler_pc_base or 0:#x}\n')
        if was: g.cont()
        return out


def until(server, g, rest):
    g.stop()
    for address in rest.split():
        g.cmd(f'break *{address}')
    # Background continue leaves GDB's command channel available if the
    # anchor never arrives. A timeout can then use the ordinary stop/dump
    # path instead of leaving subsequent commands queued behind continue.
    g.cont()
    try:
        g.read_until('Breakpoint', timeout=int(os.environ.get('UNTIL_TIMEOUT', '1800')))
    except TimeoutError:
        g.stop()
        g.cmd('delete')
        raise
    g.running = False
    out = 'Breakpoint ' + g.cmd('info registers pc')
    g.cmd('delete')
    return out


def gdb(server, g, rest):
    was = g.running; g.stop()
    out = g.cmd(rest, timeout=600)
    if os.environ.get('PROFILE_WINDOW') == 'guest' and rest.strip() == 'maintenance packet qOffsets':
        g.profiler_pc_base = 0x1018 if 'received: "00001018"' in out else None
    if was: g.cont()
    return out


server = Lov('lov', root=ROOT, run_script=str(COMMON / 'run.sh'), run_dir=RUN_DIR,
             commands={'until': until, 'gdb': gdb})

if __name__ == '__main__':
    server.main(sys.argv[1:])
