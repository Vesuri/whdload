#!/usr/bin/env python3
"""Drive Red Baron in FS-UAE through the Barto gdb stub.

  python3 tools/redbaron.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/redbaron.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, until <addr>, quit.  Here `until` gives up
after $UNTIL_TIMEOUT seconds (default 120) and fails if the breakpoint was not reached, and the
gdb pid is kept in tmp/run/<instance>/.run/gdb.pid for tools that interrupt a long command.
The run options of common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve.
"""
import os, signal, sys, threading
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.gdbserve import Gdb, Server  # noqa: F401 (Gdb: completion_host_input)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, 'tmp/run', os.environ.get('INSTANCE') or 'default', '.run')
SOCK = os.path.join(RUN, 'redbaron.sock')


class RedBaron(Server):
    def boot(self, env=None):
        g = super().boot(env)
        open(os.path.join(self.run_dir, 'gdb.pid'), 'w').write(str(g.p.pid))
        return g


def until(server, g, rest):
    g.stop()
    g.cmd(f'break *{rest}')
    timer = threading.Timer(float(os.environ.get('UNTIL_TIMEOUT', '120')),
                            lambda: g.p.send_signal(signal.SIGINT))
    timer.start()
    try:
        out = g.cmd('continue', timeout=150)
    finally:
        timer.cancel()
        g.cmd('delete')
    if 'Breakpoint ' not in out:
        raise TimeoutError('Anchor not reached: ' + out)
    return out


os.environ.setdefault('GAME', 'RedBaron')
server = game_server('redbaron', server_class=RedBaron, commands={'until': until})

if __name__ == '__main__':
    server.main(sys.argv[1:])
