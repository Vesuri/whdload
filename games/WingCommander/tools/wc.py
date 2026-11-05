#!/usr/bin/env python3
"""Drive Wing Commander in FS-UAE through the gdb stub. Products stay in tmp/.

  python3 tools/wc.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/wc.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, quit, plus until <address...> (run to the
first of these breakpoints). The run options of common/run.sh (SETUP, VARIANT, BUILD, SLAVE,
WHD_ARGS, ...) apply to serve. The server runs in its own instance, `cap` unless INSTANCE
names another, beside `make run`.
"""
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('INSTANCE', 'cap')
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import COMMON, game_server  # noqa: E402


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
    # The launcher's ownership checks instead of the shared server's unguarded pid kill.
    g.p.kill()
    subprocess.run(['/bin/bash', str(COMMON / 'run.sh'), 'stop'], check=True)
    return 'bye'


server = game_server('wc', commands={'until': until, 'quit': quit_})
if __name__ == '__main__':
    server.main(sys.argv[1:])
