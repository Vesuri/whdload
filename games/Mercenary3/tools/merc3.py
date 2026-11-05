#!/usr/bin/env python3
"""Drive Mercenary 3 in FS-UAE through the Barto gdb stub (common/tools/game_server.py).

  python3 tools/merc3.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/merc3.py <command...>   send one command to the running server, print the reply

`serve` takes common/run.sh's options from the environment: it builds and boots the release
slave, SLAVE=original boots the shipped one, SLAVE=path any other.
Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit.
Use the native build (FSUAE="$FSUAE_ARM"): it profiles the whole address space without the
lldb window fix and takes input through `gdb monitor key|mouse|input|fields`.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('merc3',
                     profile_window=not os.environ.get('FSUAE', '').endswith('fs-uae-arm/fs-uae'))

if __name__ == '__main__':
    server.main(sys.argv[1:])
