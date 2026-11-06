#!/usr/bin/env python3
"""Drive the original Stellar 7 in FS-UAE through the Barto gdb stub.

  python3 tools/stellar7.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/stellar7.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, until <addr>, quit.
The run options of common/run.sh (SETUP, VARIANT, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve.
"""
import os, sys
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, 'tmp/run', os.environ.get('INSTANCE') or 'default', '.run')
SOCK = os.path.join(RUN, 'stellar7.sock')

# The shared server fixes the stub's profiler PC window only for the x86_64 FS-UAE build;
# the native build (it answers `monitor harness`) records PCs as it is.
server = game_server('stellar7')

if __name__ == '__main__':
    server.main(sys.argv[1:])
