"""Star Wars gdb-stub server: the shared commands only (common/tools/game_server.py).

    python3 tools/starwars.py serve          boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/starwars.py wait 20        then shot, quit, ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

server = game_server('starwars')
if __name__ == '__main__':
    server.main(sys.argv[1:])
