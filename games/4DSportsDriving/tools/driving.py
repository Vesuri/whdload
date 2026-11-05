#!/usr/bin/env python3
"""Drive the original 4D Sports Driving in FS-UAE through the Barto gdb stub.

  python3 tools/driving.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/driving.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve), the emulator left running
after each unless noted: stop | cont, gdb <text>, shot <png>, profile <fields> <bin> (PAL
fields, Barto format), wait <seconds>, until <addr> (stays stopped there), quit.  BOOT_BREAK,
BOOT_CONDITION and BOOT_IGNORE stop the boot at a calibrated address.
The run options of common/run.sh (SETUP, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve;
INSTANCE=<name> runs in tmp/run/<name>/.run (default: tmp/run/default/.run).
"""
import hashlib, os, sys, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def checked_stop(g):
    """Interrupt only a target gdb still reports running: an asynchronous continue may already
    have hit a breakpoint, and interrupting an already stopped remote leaves a second stop reply
    queued, corrupting the next memory-read transaction."""
    status = g.cmd('info registers pc', timeout=30)
    if 'running' in status.lower():
        g.p.stdin.write(b'interrupt\n')
        g.p.stdin.flush()
        deadline = time.monotonic() + 10
        while True:
            time.sleep(0.2)
            status = g.cmd('info registers pc', timeout=30)
            if 'running' not in status.lower():
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('Debugger did not acknowledge stop: ' + status)
    g.running = False


def profile_window(server):
    # A private native profiler declares and verifies its built-in 24-bit window.
    expected = os.environ.get('FSUAE_NATIVE_PROFILE_SHA256')
    if expected:
        assert hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest() == expected
        return
    server.fix_profile_window()


class DrivingServer(Server):
    def boot(self, env=None):
        g = super().boot(env)
        g.stop = lambda: checked_stop(g)
        return g


server = game_server('driving', server_class=DrivingServer, profile_window=profile_window)

if __name__ == '__main__':
    os.chdir(ROOT)  # gdb scripts and relative capture paths are harness-relative
    server.main(sys.argv[1:])
