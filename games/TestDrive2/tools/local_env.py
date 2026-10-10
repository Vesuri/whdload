"""Shared Amiga paths with environment overrides: the defaults of the shared env.sh (amiga/env.sh)."""
import os

DEFAULTS = {
    'KICKSTART13': '~/.local/share/amiga/Kickstarts/kick34005.A500',
    'LHA': '~/.local/share/amiga/lha-compressor/src/lha',
    'AMIGA_TOOLCHAIN': '~/.local/opt',
    'WHDLOAD': '~/.local/share/amiga/WHDLoad-20.0',
}

def path(name):
    return os.environ.get(name) or os.path.expanduser(DEFAULTS[name])

def tool(name):
    """A m68k-amiga-elf binary from AMIGA_TOOLCHAIN, e.g. tool('objdump')."""
    return os.path.join(path('AMIGA_TOOLCHAIN'), 'bin', f'm68k-amiga-elf-{name}')
