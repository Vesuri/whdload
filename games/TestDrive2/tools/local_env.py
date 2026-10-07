"""Machine paths from amiga/local.env (ignored; see amiga/local.env.example).
NAME=value lines; values may use ${HOME} and earlier ${NAME}s. The environment wins.
"""
import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load():
    values = {}
    f = ROOT / 'amiga/local.env'
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            scope = {**values, **os.environ}
            values[name] = re.sub(r'\$\{(\w+)\}', lambda m: scope.get(m[1], ''), value)
    return {**values, **os.environ}

def path(name, *parts):
    value = load().get(name)
    if not value:
        raise SystemExit(f'{name} is not set: add it to amiga/local.env (see local.env.example)')
    return os.path.join(value, *parts)

def tool(name):
    """A m68k-amiga-elf binary from AMIGA_TOOLCHAIN, e.g. tool('objdump')."""
    return path('AMIGA_TOOLCHAIN', 'bin', f'm68k-amiga-elf-{name}')
