"""AmigaXDev's gdb-stub game server (amigaxdev.gdbserve.Server), wired to common/run.sh.

A game's tool (games/<Game>/tools/<game>.py):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
    from game_server import game_server

    def frames(server, g, rest): ...            # a game command: return the reply text
    server = game_server('tfh', commands={'frames': frames})
    if __name__ == '__main__':
        server.main(sys.argv[1:])

    python3 tools/tfh.py serve        boot (common/run.sh with DEBUG=1), attach gdb, listen
    python3 tools/tfh.py shot x.png   one command to the running server

The run options of common/run.sh (SETUP, VARIANT, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...)
apply to `serve` through the environment. The socket and the run directory are the
instance's, so instances are served side by side.
"""
import os
import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server  # noqa: E402


def game_root():
    """games/<Game> for $GAME or the current directory."""
    games = COMMON.parent / 'games'
    if os.environ.get('GAME'):
        return games / os.environ['GAME']
    here = Path.cwd().resolve()
    for p in (here, *here.parents):
        if p.parent == games and (p / 'game.conf').is_file():
            return p
    sys.exit('run this inside games/<Game> or set GAME=<Game>')


# macOS limits a Unix socket path to 104 bytes.
SOCKET_PATH_MAX = 100


def game_server(name, **kwargs):
    root = game_root()
    os.environ['GAME'] = root.name
    instance = os.environ.get('INSTANCE') or 'default'
    run_dir = f'tmp/run/{instance}/.run'
    if 'sock' not in kwargs:
        sock = str(root / run_dir / f'{name}.sock')
        if len(sock) > SOCKET_PATH_MAX:
            # A deep checkout (a worktree): the same socket by a relative path. Server and
            # client then have to be started from the same directory, as tools usually are.
            sock = os.path.relpath(sock)
            if len(sock) > SOCKET_PATH_MAX:
                sys.exit(f'socket path too long even relative to {os.getcwd()}: run from the game directory')
        kwargs['sock'] = sock
    return Server(name, root=str(root), run_script=str(COMMON / 'run.sh'),
                  run_dir=run_dir, **kwargs)
