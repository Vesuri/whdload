"""Shared bounded route boot, entry validation and runtime identity (no tracing)."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import signal
import subprocess

import _amigaxdev  # noqa: F401
from amigaxdev import gdbserve
from route_profile import ENTRY, ROOT, SLAVE


def delta(end, start):
    return (end - start) & 0xffff


@contextmanager
def deadline(seconds, stage):
    def expired(signum, frame):
        raise TimeoutError(f'{stage} exceeded {seconds:g} host seconds')
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def word(g, address):
    reply = g.cmd(f'x/1xh {address:#x}')
    match = re.search(r'^\s*0x[0-9a-f]+:\s*(0x[0-9a-f]+)\s*$', reply, re.M | re.I)
    if not match:
        raise RuntimeError(f'cannot read counter: {reply}')
    return int(match[1], 16)


def snapshot(g):
    return dict(frames=word(g, getattr(g, 'publication_counter', 0x7180)), vertb=word(g, 0x529f4),
                stamp=word(g, 0x52952), dt=word(g, 0x52954))


def at_breakpoint(g, address, timeout):
    reply = g.cmd('continue', timeout=timeout)
    pc = g.cmd('info registers pc')
    match = re.search(r'^pc\s+0x([0-9a-f]+)', pc, re.M | re.I)
    if not match or int(match[1], 16) != address or 'Breakpoint' not in reply:
        raise RuntimeError(f'expected breakpoint was not reached: {reply}\n{pc}')


def require_pal(settings):
    if settings.get('ntsc') != 'false':
        raise RuntimeError('fps.py requires a confirmed PAL configuration (ntsc=false)')


def machine_settings(run_dir):
    """Retain effective timing/memory settings, without machine-local file paths."""
    keys = {'cpu_model', 'mmu_model', 'fpu_model', 'cpu_frequency', 'cpu_speed',
            'cpu_compatible', 'cpu_cycle_exact', 'cpu_memory_cycle_exact',
            'cpu_data_cache', 'blitter_cycle_exact', 'chipmem_size', 'fastmem_size',
            'bogomem_size', 'chipset', 'ntsc', 'cachesize', 'uaeboard'}
    settings = {}
    config = Path(run_dir) / 'fsuae/Cache/Logs/debug.uae'
    for line in config.read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key in keys:
            settings[key] = value
    return settings


def configure():
    if os.environ.get('RECORD') or any(arg.startswith('--deterministic') for arg in
                                      os.environ.get('EXTRA_ARGS', '').split()):
        raise ValueError('use DETERMINISTIC=0|1 directly; RECORD and deterministic '
                         'EXTRA_ARGS overrides are not supported by route measurements')
    setup = os.environ.get('AMIGA_SETUP', 'a1200-fast')
    # Deterministic directory I/O deadlocks with the preset's indirect UAE board.
    # Keep the full 030 MMU/cache configuration; only boot I/O scheduling changes.
    deterministic = os.environ.get('DETERMINISTIC', '0' if setup == 'a1200-030' else '1')
    if deterministic not in ('0', '1'):
        raise ValueError('DETERMINISTIC must be 0 or 1')
    os.environ.update(AMIGA_SETUP=setup, DETERMINISTIC=deterministic,
                      FSUAE=os.environ.get('FSUAE') or os.environ['FSUAE_ARM'],
                      WARP='1', JOY0='none')
    print(f'route boot: {setup}, DETERMINISTIC={deterministic}', flush=True)


def timeouts():
    values = tuple(float(os.environ.get(key, default)) for key, default in
                   (('BOOT_TIMEOUT', '120'), ('RUN_TIMEOUT', '180')))
    if not all(0 < n < 86400 for n in values):
        raise ValueError('deadlines must be positive and less than one day')
    return values


def output_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(ROOT) / 'tmp'):
        raise ValueError('generated results must be stored under tmp/')
    if path.exists():
        raise ValueError('output already exists; choose a new name')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def require_instruction_backend(settings):
    if settings.get('cpu_model') not in ('68000', '68010', '68020'):
        raise RuntimeError('instruction recording is not validated for this CPU; '
                           'use MODE=counter or tools/fps.py for an untraced route')


@contextmanager
def session(boot_timeout):
    os.chdir(ROOT)
    if os.environ.get('ANCHOR', 'entry') != 'entry':
        raise ValueError('only ANCHOR=entry is supported; the 030 entry breakpoint works '
                         'with DETERMINISTIC=0')
    configure()
    server = gdbserve.Server('merc3', root=ROOT, profile_window=False)
    # Retain the owned debugger even if its constructor fails during attachment.
    original_gdb, owned = gdbserve.Gdb, []

    def tracked_gdb(*args, **kwargs):
        g = original_gdb.__new__(original_gdb)
        owned.append(g)
        original_gdb.__init__(g, *args, **kwargs)
        return g

    try:
        with deadline(boot_timeout, 'boot and entry anchor'):
            gdbserve.Gdb = tracked_gdb
            try:
                g = server.boot()
                settings = machine_settings(server.run_dir)
                require_pal(settings)
            finally:
                gdbserve.Gdb = original_gdb
            g.cmd(f'break *{ENTRY:#x}')
            at_breakpoint(g, ENTRY, boot_timeout)
            g.cmd('delete')
            # P1 retains $7180 as logic passes. Its optional publication hook has
            # a descriptor immediately before the counter; never guess from CPU type.
            opcode = word(g, 0x5a82e)
            if opcode == 0x4eb9:
                target = (word(g, 0x5a830) << 16) | word(g, 0x5a832)
                signature = b''.join(word(g, target - 12 + i).to_bytes(2, 'big')
                                     for i in range(0, 8, 2))
                if word(g, target) != 0x2f08 or word(g, target + 2) != 0x41fa:
                    raise RuntimeError('unrecognized publication hook')
                g.presentation_flag = target - 2
                if signature == b'M3PUB001':
                    g.publication_counter = target - 4
            anchor_state = snapshot(g)
            if anchor_state['frames'] != 0:
                raise RuntimeError('entry anchor did not start a fresh game')
        print('anchored at Disk.1 $4EDB0', flush=True)
        meta = dict(setup=os.environ['AMIGA_SETUP'], whd_args=os.environ.get('WHD_ARGS', ''),
                    extra_args=os.environ.get('EXTRA_ARGS', ''),
                    deterministic=os.environ['DETERMINISTIC'],
                    slave=os.path.relpath(SLAVE, ROOT),
                    slave_sha256=hashlib.sha256(Path(SLAVE).read_bytes()).hexdigest(),
                    emulator_sha256=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest(),
                    whdload_sha256=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest(),
                    launcher_sha256=hashlib.sha256(Path(os.environ['FSUAE_COMMON']).read_bytes()).hexdigest(),
                    machine=settings, anchor='entry', anchor_state=anchor_state,
                    entry_disk_offset='0x4edb0',
                    frame_counter=('P1 publications' if hasattr(g, 'publication_counter')
                                   else 'logic only (P1 release)' if hasattr(g, 'presentation_flag')
                                   else 'game $7180'),
                    boot_timeout=boot_timeout)
        yield g, meta
    finally:
        for g in owned:
            if hasattr(g, 'p'):
                g.p.kill()
                g.p.wait(timeout=5)
        subprocess.run(['/bin/bash', '-c', '. "$FSUAE_COMMON"; fsuae_stop_previous'],
                       cwd=os.path.join(ROOT, 'amiga'), check=True, timeout=10)

