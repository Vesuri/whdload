#!/usr/bin/env python3
"""Drive Test Drive in FS-UAE through the Barto gdb stub.

  python3 tools/td.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/td.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop | cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <seconds>, until <addr>, quit. The run options of
common/run.sh (SETUP, TD_SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...) apply to serve.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def checked_profile(server):
    import hashlib,json
    from pathlib import Path
    pin=json.loads((Path(ROOT)/'manifest/profiler.json').read_text())
    binary=Path(os.environ.get('FSUAE') or str(Path(os.environ.get('AMIGA_PREFIX', str(Path.home()/'.local')))/'fs-uae/fs-uae'))
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    native=json.loads((Path(ROOT)/'manifest/native-input.json').read_text())
    if digest==native['sha256']:
        return  # Reviewed native build profiles the full 24-bit address space.
    if digest!=pin['sha256']:
        raise RuntimeError('FS-UAE changed; run check_profiler.py before tracing')
    server.fix_profile_window()

server = game_server('td', profile_window=checked_profile)
SOCK = server.sock

if __name__ == '__main__':
    server.main(sys.argv[1:])
