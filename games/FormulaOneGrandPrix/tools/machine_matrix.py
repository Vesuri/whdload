#!/usr/bin/env python3
"""Serial, fresh-boot B5/A7/A8 captures; outputs are immutable below tmp/.
Source amiga/env.sh. Usage: machine_matrix.py MACHINE on|off clock|green|tow|follow|all OUT [FIELDS]
MMU cells are functional only; fixed-clock cells explicitly select cycle-exact cores.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from slave_inputs import ROOT, verify
from slave_compare import client

MACHINES = {
    'a500': ('a500-1.5m', '', ''),
    'a1200': ('a1200', '', ''),
    '020': ('a1200-fast', '', ''),
    '030': ('a1200-030', '--uae_mmu_model=0 --cpu=68030', 'NOMMU'),
    '030-mmu': ('a1200-030', '', 'MMU'),
    '040': ('a1200-040', '--cpu=68040-NOMMU --uae_mmu_model=0 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true', 'NOMMU'),
    '060': ('a1200-060', '--cpu=68060-NOMMU --uae_mmu_model=0 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true', 'NOMMU'),
    '040-mmu': ('a1200-040', '', 'MMU'),
    '060-mmu': ('a1200-060', '', 'MMU'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime():
    pins = json.loads((ROOT/'manifest/runtime-inputs.json').read_text())
    for key, expected in pins.items():
        if sha(os.environ[key]) != expected:
            raise ValueError(f'runtime input changed: {key}')
    return pins


def capture(machine, caches, command, destination, fields=100):
    verify()
    pins = runtime()
    setup, extra, mmu = MACHINES[machine]
    # Keep host mouse activity from auto-switching a disabled capture port.
    extra = (extra + ' --joystick_port_0_autoswitch=0').strip()
    custom3 = int(os.environ.get('MATRIX_CUSTOM3', '0'), 0)
    instant = os.environ.get('MATRIX_INSTANT_BLITTER', '0')
    skip_intro = os.environ.get('MATRIX_SKIP_INTRO', '0')
    anchor_method = os.environ.get('RACE_ANCHOR', 'screen')
    if custom3 < 0 or custom3 & ~3 or instant not in ('0', '1') or skip_intro not in ('0', '1'):
        raise ValueError('invalid developer ceiling options')
    if instant == '1':
        extra += ' --uae_immediate_blits=true'
    if caches not in ('on', 'off') or command not in ('clock', 'green', 'tow', 'follow', 'all'):
        raise ValueError('invalid cache/command selection')
    out = Path(destination).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('captures must stay in tmp/')
    slave = ROOT/os.environ.get('MATRIX_SLAVE', 'tmp/build-verify/F1GP.Slave')
    build = json.loads((slave.parent/'build.json').read_text())
    if build['slave_sha256'] != sha(slave) or build['source_sha256'] != sha(ROOT/'whdload/F1GP.s'):
        raise ValueError('stale build')
    if custom3 or instant == '1':
        if build['build'] not in ('developer', 'verify') or command != 'green' or anchor_method != 'start-state':
            raise ValueError('ceiling options require a developer/VERIFY green start-state capture')
    sock = ROOT/'amiga/.run/f1gp.sock'
    if sock.exists():
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(1)
        try:
            s.connect(str(sock))
        except ConnectionRefusedError:
            sock.unlink()
        else:
            raise RuntimeError('another project server is active; stop it explicitly')
        finally:
            s.close()
    out.mkdir(parents=True, exist_ok=False)
    args = f'CUSTOM1={skip_intro} CUSTOM2={int(caches == "on")} CUSTOM3={custom3} CUSTOM4=0 CUSTOM5=0 {mmu}'
    if caches == 'off':
        args += ' NoCache'
    if build['build'] == 'verify':
        args += ' FileLog'
    env = dict(os.environ, AMIGA_SETUP=setup, EXTRA_ARGS=extra, WHD_ARGS=args,
               SLAVE=str(slave), WARP='1', DETERMINISTIC='1', JOY0='none', JOY1='none',
               RACE_LEADS='0,0,0', RACE_ANCHOR=anchor_method, VERIFY_EXIT='1', FSUAE=os.environ['FSUAE_ARM'])
    for key in ('ROUTE_SHOTS', 'RACE_KEEP_TRACES', 'CPU', 'FAST_KB', 'SLOW_KB', 'CHIP_KB'):
        env.pop(key, None)
    meta = dict(status='INCOMPLETE', machine=machine, caches=caches, command=command,
                setup=setup, extra_args=extra, whd_args=args, build=build, runtime=pins,
                fields=fields, skip_intro=skip_intro, custom3=custom3, instant_blitter=instant, anchor_method=anchor_method, tools={p.name: sha(p) for p in (ROOT/'tools').glob('*.py')})
    (out/'capture.json').write_text(json.dumps(meta, indent=2)+'\n')
    shutil.copy(slave, out/'slave.bin')
    log = out/'serve.log'
    with log.open('w') as f:
        proc = subprocess.Popen([sys.executable, 'tools/f1gp.py', 'serve'], cwd=ROOT,
                                env=env, stdout=f, stderr=subprocess.STDOUT)
    ready = False
    try:
        end = time.monotonic()+180
        while 'serving on ' not in log.read_text():
            if proc.poll() is not None or time.monotonic() > end:
                raise RuntimeError('server boot failed: '+log.read_text()[-2000:])
            time.sleep(.2)
        ready = True
        # A spelling accepted on 040/060 need not exist on 030. Reject silent
        # CPU fallback before collecting any game evidence.
        debug = ROOT/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt'
        reports = re.findall(r'CPU=(\d+), FPU=(\d+).*?MMU=(\d+), JIT=(\d+)',
                             debug.read_text(errors='replace'))
        cpu = {'a500': 68000, 'a1200': 68020, '020': 68020,
               '030': 68030, '040': 68040, '060': 68060}[machine.split('-')[0]]
        expected_mmu = cpu if machine.endswith('-mmu') else 0
        if not reports or tuple(map(int, reports[-1]))[::2] != (cpu, expected_mmu):
            raise ValueError(f'effective CPU/MMU mismatch: {reports[-1:]}; expected {cpu}/{expected_mmu}')
        meta['effective_cpu_report'] = list(map(int, reports[-1]))
        config = debug.with_name('debug.uae')
        if config.exists():
            shutil.copy(config, out/'debug.uae')
        if command == 'clock':
            meta['result'] = client('raceclock', str(out))
        else:
            meta['result'] = client('raceprofile', command, str(out), str(fields))
        print(meta['result'], flush=True)
        marker = ROOT/'amiga/.run/dh0/whdload-exit.txt'
        if marker.exists():
            raise RuntimeError('WHDLoad returned before F10')
        client('gdb', 'monitor key 59 1')
        client('gdb', 'monitor fields 1000')
        client('gdb', 'monitor key 59 0')
        client('shot', str(out/'quit.png'))
        meta['quit'] = marker.read_text().strip() if marker.exists() else 'MISSING'
        if meta['quit'] != 'OK':
            raise RuntimeError('F10 did not return cleanly')
        meta['status'] = 'CAPTURED'  # review evidence; capture alone is not a gate pass
    except Exception as error:
        meta.update(status='FAIL', error=str(error))
        # The debugger may be disconnected. Do not ask the shared shot command
        # to reuse its old trace and mislabel that image as the failed machine.
        raise
    finally:
        for path in (ROOT/'amiga/.run/dh1').rglob('.whdl*'):
            if path.is_file():
                shutil.copy(path, out/path.name)
        shutil.copy(ROOT/'amiga/.run/fsuae.log', out/'fsuae.log')
        debuglog = ROOT/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt'
        if debuglog.exists():
            shutil.copy(debuglog, out/'emulator-debug.log')
        (out/'capture.json').write_text(json.dumps(meta, indent=2)+'\n')
        if ready:
            try:
                client('quit', quiet=True)
            except RuntimeError:
                if meta['status'] != 'FAIL':
                    raise
        proc.wait(timeout=30)


if __name__ == '__main__':
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    capture(*sys.argv[1:5], int(sys.argv[5]) if len(sys.argv) == 6 else 100)
