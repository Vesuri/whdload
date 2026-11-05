#!/usr/bin/env python3
"""Drive the original Powerdrome in FS-UAE through the Barto gdb stub.

  python3 tools/powerdrome.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/powerdrome.py <command...>   send one command to the running server, print the reply

Commands (the emulator is left running after each unless noted):
  stop | cont                  halt / resume the CPU
  gdb <text>                   raw gdb CLI command (halts first, resumes after)
  shot <png>                   record one field, save its screenshot
  profile <fields> <bin>       cycle-exact trace of <fields> PAL fields (Barto format)
  wait <seconds>               let it run
  until <addr>                 run to a breakpoint at addr and stay stopped there
  quit                         kill gdb and the emulator
"""
import os, signal, socket, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev.gdbserve import BASETEXT_VM, Gdb, Server  # noqa: E402

SENT = '@@POWERDROME-DONE@@'


def send_request(connection, message):
    payload=message.encode()
    connection.sendall(f'PD1 {len(payload)}\n'.encode()+payload)


def receive_request(connection):
    # Explicit byte lengths work with fragmented streams and still-open clients.
    header=bytearray()
    while not header.endswith(b'\n'):
        byte=connection.recv(1)
        if not byte: raise EOFError('Request ended before its length header')
        header.extend(byte)
        if len(header)>64: raise ValueError('Invalid request length header')
    if not header.startswith(b'PD1 '): raise ValueError('Expected PD1 request framing')
    size=int(header[4:].strip())
    if not 0<=size<=8*1024*1024: raise ValueError('Request size outside supported range')
    chunks=[]
    while size:
        chunk=connection.recv(min(65536,size))
        if not chunk: raise EOFError('Request ended before all payload bytes arrived')
        chunks.append(chunk);size-=len(chunk)
    return b''.join(chunks).decode().strip()


# The x86_64 stub's profiler window (amigaxdev.gdbserve), fixed in one batch lldb attach.
LLDB_FIX = (
    'script t=lldb.debugger.GetSelectedTarget(); h=t.GetModuleAtIndex(0).GetObjectFileHeaderAddress(); '
    'a=h.GetLoadAddress(t)-h.GetFileAddress()+%d; e=lldb.SBError(); p=t.GetProcess(); '
    'p.WriteMemory(a, (0).to_bytes(4,"little")+(0x7fffffff).to_bytes(4,"little"), e); '
    'print("WINDOW", p.ReadMemory(a, 8, e).hex())')


def fix_profile_window(fields=100):
    # One attach that computes the slide and writes the window: each lldb attach to this
    # x86_64 (Rosetta) process costs ~40 s, so the earlier image-list-then-write pair could
    # exceed a 60 s timeout.
    pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
    assert 1 <= fields <= 500, 'Capture limit is 500 PAL fields'
    fix = LLDB_FIX % BASETEXT_VM
    if fields > 100:
        # Command parser clamps requests to 100. Bypass that clamp only in this
        # emulator process; do not modify the installed executable or guest code.
        # x86_64: cmovl ecx,eax -> mov ecx,eax; nop (keep requested field count).
        fix += ('; a=h.GetLoadAddress(t)-h.GetFileAddress()+0x5bfbe; '
                'old=p.ReadMemory(a,3,e); assert old in (bytes.fromhex("0f4cc8"),bytes.fromhex("89c190")); '
                'p.WriteMemory(a,bytes.fromhex("89c190"),e); '
                'assert p.ReadMemory(a,3,e)==bytes.fromhex("89c190"); print("LONG_CAPTURE_READY")')
    out = subprocess.run(['lldb', '-p', pid, '--batch', '-o', fix],
                         capture_output=True, text=True, timeout=300).stdout
    assert 'WINDOW 00000000ffffff7f' in out, out
    if fields > 100: assert 'LONG_CAPTURE_READY' in out.splitlines(), out


class Powerdrome(Server):
    """The shared server with PD1 request framing and captures of up to 500 fields."""

    def serve(self):
        g = self.boot()
        # Arm an address learned in a calibration boot before emulated time advances.
        # This prevents a fast warp boot from passing the first race during host polling.
        if os.environ.get('BOOT_BREAK'):
            g.cmd(f"break *{os.environ['BOOT_BREAK']}")
            print(g.cmd('continue', timeout=1800), flush=True)
            g.cmd('delete')
        else:
            g.cont()
        if os.path.exists(self.sock):
            os.unlink(self.sock)
        s = socket.socket(socket.AF_UNIX); s.bind(self.sock); s.listen(1)
        print('serving on', self.sock, flush=True)
        while True:
            c, _ = s.accept()
            line = ''
            try:
                c.settimeout(30)
                line = receive_request(c)
                reply = self.handle(g, line)
            except Exception as e:  # report and keep serving
                reply = f'ERROR {type(e).__name__}: {e}'
            try:
                c.sendall((reply + '\n').encode())
            except OSError:
                pass
            c.close()
            if line == 'quit':
                break

    def capture(self, g, fields, target):
        was = g.running; g.stop()
        fix_profile_window(int(fields))
        out = g.cmd(f'monitor profile {fields} "" "{target}"', timeout=1800)
        if was: g.cont()
        return out

    def request(self, line):
        c = socket.socket(socket.AF_UNIX); c.connect(self.sock)
        send_request(c, line)
        out = b''
        while chunk := c.recv(65536):
            out += chunk
        return out.decode()


def quit(server, g, rest):
    g.p.kill()
    pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
    try:
        os.kill(int(pid), signal.SIGKILL)
    except ProcessLookupError:
        pass
    return 'bye'


# The run options of common/run.sh (SLAVE, BUILD, WHD_ARGS, CPU, FAST_KB, INSTANCE, ...) apply
# to serve through the environment; the run directory is the instance's.
server = game_server('powerdrome', server_class=Powerdrome, sentinel=SENT, commands={'quit': quit})
RUN, SOCK = server.run_dir, server.sock

if __name__ == '__main__':
    server.main(sys.argv[1:])
