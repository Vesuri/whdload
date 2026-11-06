#!/usr/bin/env python3
"""The validation machines: AmigaXDev named setups, always NTSC.

resolve() asks the shared launcher's fsuae_setup for a named machine's values, so
captures run exactly what `make run SETUP=<name> NTSC=1` runs. The game's SETUPS in
game.conf lists the same machines.
"""
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT.parent.parent/'common'
# 15 Hz Sim68000 build; 60 Hz Sim60 on a typical A1200; 60 Hz Sim60 at the fast end.
MACHINES = ('a500-1.5m', 'a1200-fast', 'a1200-060')
SETTINGS = ('CPU', 'AMIGA_MODEL', 'CHIP_KB', 'FAST_KB', 'SLOW_KB', 'KICKSTART')
# Variables that choose a machine. The shared env.sh exports a default KICKSTART, so it
# does not; it is still dropped for named setups, which bring their own ROM.
SELECTORS = SETTINGS[:-1]

_SCRIPT = r'''. "$1/env.sh" && . "$FSUAE_COMMON" && fsuae_setup >/dev/null || exit 1
printf '%s\n' "$CPU" "$AMIGA_MODEL" "$CHIP_KB" "$FAST_KB" "$SLOW_KB" "$KICKSTART"
printf '%s\n' "${FSUAE_SETUP_ARGS[@]}"'''


def resolve(name, ntsc=1):
    """Return the named machine's settings and the FS-UAE arguments it launches with."""
    env = {key: value for key, value in os.environ.items() if key not in SETTINGS}
    env.update(AMIGA_SETUP=name, NTSC=str(ntsc))
    lines = subprocess.run(['/bin/bash', '-c', _SCRIPT, 'machines', str(COMMON)], env=env,
                           check=True, capture_output=True, text=True).stdout.splitlines()
    cpu, model, chip, fast, slow, kickstart = lines[:6]
    return dict(setup=name, cpu=cpu, model=model, chip_kb=int(chip), fast_kb=int(fast),
                slow_kb=int(slow), kickstart=kickstart, ntsc_mode=ntsc, args=lines[6:])


def env(name, ntsc=1):
    """Environment for common/run.sh and fixed_window.py: the named setup only."""
    environment = {key: value for key, value in os.environ.items()
                   if key not in SETTINGS+('AMIGA_SETUP', 'EXTRA_ARGS')}
    environment.update(SETUP=name, NTSC=str(ntsc))
    return environment


def default_setup():
    """game.conf's SETUP: the machine common/run.sh boots when none is given."""
    match = re.search(r'^SETUP=(\S+)', (ROOT/'game.conf').read_text(), re.M)
    return match[1] if match else 'a500'


def effective(environment):
    """The named setup a launch with this environment boots, or None for custom.

    Explicit machine variables without a SETUP keep their meaning: SETUP=custom.
    """
    name = environment.get('AMIGA_SETUP') or environment.get('SETUP')
    if not name:
        name = 'custom' if any(environment.get(key) for key in SELECTORS) else default_setup()
    return None if name == 'custom' else name
