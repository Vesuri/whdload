#!/usr/bin/env python3
"""Shared debugger server, adapted from Legends of Valour. Products stay in tmp/."""
import os
from pathlib import Path
import subprocess
import sys
import _amigaxdev
from amigaxdev.gdbserve import Server

ROOT = Path(__file__).resolve().parents[1]
CAP = os.environ.get('FSUAE_RUN', '../tmp/cap')

def until(server, g, rest):
    g.stop()
    for address in rest.split():
        g.cmd(f'break *{address}')
    g.cont()
    try:
        g.read_until('Breakpoint', timeout=int(os.environ.get('UNTIL_TIMEOUT', '60')))
        g.running = False
        return 'Breakpoint ' + g.cmd('info registers pc')
    finally:
        g.stop()
        g.cmd('delete')

def quit_(server, g, rest):
    # Use the shared launcher ownership checks instead of Server's unguarded PID kill.
    g.p.kill()
    subprocess.run(['/bin/bash', str(ROOT/'amiga/run.sh'), 'stop'],
                   env=dict(os.environ, FSUAE_RUN=CAP), check=True)
    return 'bye'

class WingCommander(Server):
    def boot(self, env=None):
        os.chdir(ROOT)
        return super().boot(dict(env or {}, FSUAE_RUN=CAP))

server = WingCommander('wc', root=str(ROOT), run_dir='amiga/'+CAP,
                       commands={'until': until, 'quit': quit_})
if __name__ == '__main__':
    server.main(sys.argv[1:])
