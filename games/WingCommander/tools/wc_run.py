"""Boot the game from the harness through common/run.sh, one run instance per capture.

    env = wc_run.run_env(out, variant='ocs', SLAVE=..., WHD_ARGS=...)
    g = wc_run.server('wc-gate', env).boot(env)      # DEBUG=1 boot with the gdb stub
    wc_run.launch(env)                               # a plain boot
    wc_run.drawer(env) / 'WingCommander.Slave'       # the booted game drive (DH1)
    wc_run.stop(env)

A capture directory below tmp/ names its own run instance (common/run.sh INSTANCE), so the
emulator, its drives and its gdb-stub port are the capture's, under tmp/run/<instance>/.run/.
Screenshots go to that directory's shots/. Reports read a capture's drive with
capture_drawer(out).
"""
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUN_SH = ROOT.parents[1]/'common/run.sh'
# The harness's variant names and the package's (game.conf VARIANTS).
VARIANTS = {'cd32': 'WingCommanderCD32', 'ocs': 'WingCommander'}


def instance(out):
    """The run instance of a capture directory below tmp/."""
    relative = Path(out).resolve().relative_to((ROOT/'tmp').resolve())
    return re.sub(r'[^A-Za-z0-9_-]', '_', '-'.join(relative.parts))


def run_dir(env):
    return ROOT/'tmp/run'/env['INSTANCE']/'.run'


def drawer(env):
    """The game drive of the last boot: a fresh copy of tmp/game/<drawer> with the slave."""
    return run_dir(env)/'dh1'


def capture_drawer(out):
    return ROOT/'tmp/run'/instance(out)/'.run/dh1'


def run_env(out, base=None, variant=None, **values):
    """The environment for booting the capture `out`: the caller's (or `base`), the
    capture's instance, the variant ('cd32' or 'ocs') and the given run options."""
    env = dict(os.environ if base is None else base)
    for key in ('FSUAE_RUN', 'CALLER_DIR'):
        env.pop(key, None)
    env.update(GAME=ROOT.name, INSTANCE=instance(out))
    if variant:
        env['VARIANT'] = VARIANTS[variant]
    env.update(values)
    if env.get('SLAVE') and env['SLAVE'] != 'original':
        env['SLAVE'] = str(Path(env['SLAVE']).resolve())
    env['FSEMU_SCREENSHOTS_DIR'] = str(run_dir(env)/'shots')
    return env


def launch(env, *args, **kwargs):
    """common/run.sh [run|stop] with this environment."""
    return subprocess.run(['/bin/bash', str(RUN_SH), *args], cwd=ROOT, env=env, check=True, **kwargs)


def stop(env):
    launch(env, 'stop')


def server(name, env, **kwargs):
    """AmigaXDev's gdb-stub server on common/run.sh in this capture's run directory."""
    import _amigaxdev  # noqa: F401 (finds amigaxdev)
    from amigaxdev.gdbserve import Server
    return Server(name, root=str(ROOT), run_script=os.path.relpath(RUN_SH, ROOT),
                  run_dir=os.path.relpath(run_dir(env), ROOT), **kwargs)
