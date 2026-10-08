#!/usr/bin/env python3
"""Drive the original Legends of Valour in FS-UAE through the Barto gdb stub.

  python3 tools/lov.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/lov.py <command...>   send one command to the running server, print the reply

Commands (the emulator is left running after each unless noted):
  stop | cont                  halt / resume the CPU
  gdb <text>                   raw gdb CLI command (halts first, resumes after)
  shot <png>                   record one field, save its screenshot
  profile <fields> <bin>       cycle-exact trace of <fields> PAL fields (Barto format)
  wait <seconds>               let it run
  until <addr>                 run to a breakpoint at addr and stay stopped there
  quit                         kill gdb and the emulator
"""
import os, select, signal, socket, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import barto
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Captures run in amiga/.cap (FSUAE_RUN), apart from interactive amiga/run.sh sessions in
# amiga/.run: run.sh stops the emulator its run directory last started.
CAP = os.environ.get('FSUAE_RUN', '.cap')
RUN = os.path.join(ROOT, 'amiga', CAP)
SOCK = os.path.join(RUN, 'lov.sock')
GDB = os.path.expanduser('~/.local/opt/bin/m68k-amiga-elf-gdb')
# gdb runs in the repo root and cannot quote file names, so dump paths are given relative to
# it (SCRATCH), clear of the space in the checkout path.
SCRATCH = 'tmp/scratch'
SENT = '@@LOV-DONE@@'


class Gdb:
    def __init__(self, port):
        env = dict(os.environ, HOME=os.path.join(RUN, 'gdbhome'))
        os.makedirs(env['HOME'], exist_ok=True)
        os.makedirs(os.path.join(ROOT, SCRATCH), exist_ok=True)
        self.p = subprocess.Popen([GDB, '-q', '-nx'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, env=env, cwd=ROOT, bufsize=0)
        self.buf = b''
        self.running = False
        self.profiler_pc_base = None
        for c in ('set pagination off', 'set confirm off', 'set height 0', 'set width 0',
                  'set remotetimeout 120', 'set architecture m68k'):
            self.cmd(c)
        out = self.cmd(f'target remote 127.0.0.1:{port}', timeout=60)
        if 'Remote debugging' not in out and 'in ??' not in out and '0x' not in out:
            raise RuntimeError('connect failed:\n' + out)

    def read_until(self, token, timeout):
        end = time.time() + timeout
        while token.encode() not in self.buf:
            r, _, _ = select.select([self.p.stdout], [], [], max(0, end - time.time()))
            if not r:
                raise TimeoutError(self.buf.decode(errors='replace'))
            chunk = os.read(self.p.stdout.fileno(), 65536)
            if not chunk:
                raise EOFError(self.buf.decode(errors='replace'))
            self.buf += chunk
        i = self.buf.index(token.encode())
        out, self.buf = self.buf[:i], self.buf[i + len(token):]
        return out.decode(errors='replace')

    def cmd(self, text, timeout=30):
        self.p.stdin.write((text + f'\necho {SENT}\\n\n').encode())
        out = self.read_until(SENT, timeout)
        return out.replace('(gdb) ', '').strip()

    def cont(self):
        if not self.running:
            self.p.stdin.write(b'continue &\n')
            time.sleep(0.2)
            self.running = True

    def stop(self):
        if self.running:
            self.p.stdin.write(b'interrupt\n')
            self.cmd('', timeout=30)
            time.sleep(0.3)
            self.running = False


# This FS-UAE build's Barto stub (x86_64, ~/.local/fs-uae) leaves the profiler's PC window
# [baseText, baseText+sizeText) as [0x0100007f, +0) when no --remote_debugger_trigger is given
# (127.0.0.1 lands in baseText), so every trace record comes out without a PC.  Under WHDLoad no
# trigger can name the game, so set the window to everything through lldb before each capture.
# Addresses are this binary's link-time ones (baseText = 0x32dea04, read by start_cpu_profiler).
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


def serve():
    env = dict(os.environ, DEBUG='1', SILENT=os.environ.get('SILENT', '1'), FSUAE_RUN=CAP)
    out = subprocess.run(['bash', os.path.join(ROOT, 'amiga/run.sh')], env=env,
                         capture_output=True, text=True, check=True).stdout
    print(out, end='', flush=True)
    port = int(out.rsplit('port ', 1)[1].split(')')[0])
    for _ in range(80):
        if subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN'], capture_output=True).stdout:
            break
        time.sleep(0.25)
    g = Gdb(port)
    print('attached; pc', g.cmd('info registers pc'), flush=True)
    # Arm an address learned in a calibration boot before emulated time advances.
    # This prevents a fast warp boot from passing the first race during host polling.
    if os.environ.get('BOOT_BREAK'):
        g.cmd(f"break *{os.environ['BOOT_BREAK']}")
        print(g.cmd('continue', timeout=1800), flush=True)
        g.cmd('delete')
    else:
        g.cont()
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    s = socket.socket(socket.AF_UNIX); s.bind(SOCK); s.listen(1)
    print('serving on', SOCK, flush=True)
    while True:
        c, _ = s.accept()
        line = c.recv(65536).decode().strip()
        try:
            reply = handle(g, line)
        except Exception as e:  # report and keep serving
            reply = f'ERROR {type(e).__name__}: {e}'
        try:
            c.sendall((reply + '\n').encode())
        except OSError:
            pass
        c.close()
        if line == 'quit':
            break


def handle(g, line):
    op, _, rest = line.partition(' ')
    if op == 'stop':
        g.stop(); return g.cmd('info registers pc')
    if op == 'cont':
        g.cont(); return 'running'
    if op == 'wait':
        g.cont(); time.sleep(float(rest)); return 'ok'
    if op == 'until':
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
    if op == 'gdb':
        was = g.running; g.stop()
        out = g.cmd(rest, timeout=600)
        if os.environ.get('PROFILE_WINDOW') == 'guest' and rest.strip() == 'maintenance packet qOffsets':
            g.profiler_pc_base = 0x1018 if 'received: "00001018"' in out else None
        if was: g.cont()
        return out
    if op in ('shot', 'profile'):
        was = g.running; g.stop()
        if op == 'shot':
            target, fields, png = os.path.join(RUN, 'shot.bin'), 1, os.path.abspath(rest)
        else:
            fields, target = rest.split(None, 1)
            target = os.path.abspath(target)
        if op == 'profile':
            if os.environ.get('PROFILE_WINDOW') == 'guest':
                assert g.profiler_pc_base == 0x1018, 'guest profiler handshake was not acknowledged'
            else:
                fix_profile_window()
                g.profiler_pc_base = 0
        out = g.cmd(f'monitor profile {fields} "" "{target}"', timeout=1800)
        Path(target).with_suffix('.pc-base').write_text(f'{g.profiler_pc_base or 0:#x}\n')
        if was: g.cont()
        if op == 'shot':
            f = barto.load(target).fields[-1]
            open(png, 'wb').write(f.shot)
            return f'{png} kind={f.shot_kind} {len(f.shot)} bytes {out}'
        return out or 'ok'
    if op == 'quit':
        g.p.kill()
        pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
        os.kill(int(pid), signal.SIGKILL)
        return 'bye'
    return 'unknown command'


def client(args):
    c = socket.socket(socket.AF_UNIX); c.connect(SOCK)
    c.sendall(' '.join(args).encode())
    out = b''
    while chunk := c.recv(65536):
        out += chunk
    print(out.decode(), end='')


if __name__ == '__main__':
    if sys.argv[1:] == ['serve']:
        serve()
    else:
        client(sys.argv[1:])
