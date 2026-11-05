#!/usr/bin/env python3
"""Drive the original Hard Drivin' in FS-UAE through the Barto gdb stub.

  python3 tools/harddrivin.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/harddrivin.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, until <addr>, quit.  Here:
  profile <fields> <bin>       1..1100 fields; over 100 lifts the stub's clamp through lldb, and
                               HD_PROFILE_DIRECT=1 uses the patched profiler emulator instead
  gdb <text>                   with a 30-minute timeout
  host <lldb command>          an lldb command against the emulator process
  poke <args>                  tools/host_poke.py's hd-poke, verified
The run options of common/run.sh (SETUP, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve;
INSTANCE=<name> runs in tmp/run/<name>/.run (default: tmp/run/default/.run). START_STOPPED=1
leaves the CPU halted after boot; lldb's commands and replies are logged to .run/lldb-control.log.
"""
import os, re, shutil, sys, time
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.gdbserve import BASETEXT_VM, Lldb, Server
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, 'tmp/run', os.environ.get('INSTANCE') or 'default', '.run')


class LoggedLldb(Lldb):
    def cmd(self, text, timeout=60):
        result = super().cmd(text, timeout)
        with open(os.path.join(RUN, 'lldb-control.log'), 'a') as log:
            log.write(text + '\n' + result + '\n')
        return result


class HardDrivin(Server):
    def boot(self, env=None):
        os.chdir(ROOT)
        g = super().boot(env)
        open(os.path.join(self.run_dir, 'gdb.pid'), 'w').write(str(g.p.pid))
        if os.environ.get('START_STOPPED') and not os.environ.get('BOOT_BREAK'):
            resume = g.cont

            def skip_once():  # serve's resume after boot; later ones run
                g.cont = resume
            g.cont = skip_once
        return g

    def fix_profile_window(self):
        if self.lldb is None:
            self.lldb = LoggedLldb(self.run_dir, self.sent)
        super().fix_profile_window()


def host(server, g, rest):
    server.fix_profile_window()
    return server.lldb.cmd(rest)


def poke(server, g, rest):
    g.stop()
    if server.lldb is None:
        server.fix_profile_window()
    L = server.lldb
    L.cmd('process interrupt')
    while 'stopped' not in L.cmd('process status'):
        time.sleep(.1)
    if not getattr(L, 'poke_loaded', False):
        L.cmd('command script import "' + os.path.join(ROOT, 'tools/host_poke.py') + '"')
        L.poke_loaded = True
    out = L.cmd('hd-poke ' + rest, timeout=120)
    L.cmd('process continue')
    assert 'VERIFIED' in out, out
    return out


def gdb(server, g, rest):
    was = g.running
    g.stop()
    out = g.cmd(rest, timeout=1800)
    if was:
        g.cont()
    return out


def profile(server, g, rest):
    fields, target = rest.split(None, 1)
    target = os.path.abspath(target)
    was = g.running
    g.stop()
    fields = int(fields)
    if not 1 <= fields <= 1100:
        raise ValueError('fields must be 1..1100')
    direct = os.environ.get('HD_PROFILE_DIRECT') == '1'
    if direct:
        raw = open(os.environ['FSUAE'], 'rb').read()
        assert raw[0x5f380-0x4000:0x5f38c-0x4000] == bytes.fromhex('31ff90909090beffffff7f90')
        assert raw[0x5bfb9-0x4000:0x5bfbe-0x4000] == bytes.fromhex('89c1909090')
    else:
        server.fix_profile_window()
    if fields > 100 and not direct:
        # This x86_64 build clamps the monitor request to 100 fields.
        # One-shot host breakpoint changes only its capture length, before
        # the store and trace header; no guest instruction or state changes.
        L = server.lldb
        binary = os.environ.get('FSUAE') or shutil.which('fs-uae')
        raw = open(binary, 'rb').read()
        assert raw[0x5bfb6-0x4000:0x5bfbe-0x4000] == bytes.fromhex('83f864b964000000')
        L.cmd('process interrupt')
        while 'stopped' not in L.cmd('process status'):
            time.sleep(.1)
        bp = L.base - BASETEXT_VM + 0x5bfd1
        count_addr = L.base - BASETEXT_VM + 0x32dea50
        out = L.cmd(f'breakpoint set --address {bp:#x} --one-shot true --auto-continue true -C "memory write -s4 {count_addr:#x} {fields:#x}"')
        assert re.search(r'Breakpoint \d+:', out), out
        L.cmd('process continue')
    out = g.cmd(f'monitor profile {fields} "" "{target}"', timeout=1800)
    if was:
        g.cont()
    return out or 'ok'


server = game_server('harddrivin', server_class=HardDrivin,
                     commands={'host': host, 'poke': poke, 'gdb': gdb, 'profile': profile})

if __name__ == '__main__':
    server.main(sys.argv[1:])
