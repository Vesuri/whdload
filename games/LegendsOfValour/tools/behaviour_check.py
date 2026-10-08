#!/usr/bin/env python3
"""Snapshot the first start-screen button poll, without a tape (original or rebuilt slave).
Two boots: learn h6 in the first, arm its first hit before reset advances in the second.
Use only amiga/.cap; retain all game-derived material under tmp/.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from lov import SCRATCH
from lov_report import regions

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('out', type=Path)
p.add_argument('--slave', type=Path)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
source_slave = a.slave or ROOT/'tmp/game/LegendsOfValour/LegendsOfValour.Slave'
shutil_source = source_slave.resolve()
import shutil
shutil.copy2(shutil_source, a.out/'slave.slave')
a.slave = a.out/'slave.slave'
env = dict(os.environ, FSUAE_RUN='.cap', JOY0='none', CHIP_KB='512', FAST_KB='0',
           EXTRA_ARGS='--slow_memory=1536', DETERMINISTIC='1', WARP='1', WHD_ARGS='CUSTOM2=0')
if a.slave:
    env['SLAVE'] = str(a.slave.resolve())
else:
    env.pop('SLAVE', None)
    os.environ.pop('SLAVE', None)
if a.slave:
    os.environ['SLAVE'] = str(a.slave.resolve())
sock = ROOT/'amiga/.cap/lov.sock'
def command(*args):
    return subprocess.check_output([sys.executable, str(ROOT/'tools/lov.py'), *args], env=env, text=True, stderr=subprocess.PIPE)
def boot(anchor=None):
    if anchor:
        env['BOOT_BREAK'] = hex(anchor)
    log = (a.out/('anchor-serve.log' if anchor else 'calibration-serve.log')).open('w')
    process = subprocess.Popen([sys.executable, str(ROOT/'tools/lov.py'), 'serve'], env=env, stdout=log, stderr=log)
    for _ in range(180):
        log.flush()
        if 'serving on' in Path(log.name).read_text():
            return process
        if process.poll() is not None:
            raise RuntimeError(Path(log.name).read_text())
        time.sleep(1)
    raise RuntimeError('server did not start')
def dump(name, start, end):
    temporary = f'{SCRATCH}/lov-behaviour-{os.getpid()}.bin'
    reply = command('gdb', f'dump binary memory {temporary} {start:#x} {end:#x}')
    if 'ERROR' in reply:
        raise RuntimeError(reply)
    path = ROOT/temporary
    data = path.read_bytes()
    path.unlink()
    (a.out/name).write_bytes(data)
    return data
if sock.exists():
    try:
        command('quit')
    except (subprocess.CalledProcessError, ConnectionRefusedError):
        pass
process = None
try:
    process = boot()
    for _ in range(60):
        command('wait', '0.5')
        code = dump('calibration.bin', 0xc00000, 0xd80000)
        r = {name: lo for lo, hi, name, origin in regions(code, 0xc00000)}
        if 'h6' in r:
            break
    else:
        raise RuntimeError('h6 never appeared')
    anchor = r['h6']+0x76c
    command('quit'); process.wait(timeout=10)
    process = boot(anchor)
    code = dump('code.bin', 0xc00000, 0xd80000)
    chip = dump('chip.bin', 0, 0x80000)
    r = {name: lo for lo, hi, name, origin in regions(code, 0xc00000, chip)}
    def read(address, size):
        if address < len(chip):
            return chip[address:address+size]
        return code[address-0xc00000:address-0xc00000+size]
    def number(address, size):
        return int.from_bytes(read(address,size),'big')
    width = number(r['h12']+0x2e,2); height = number(r['h12']+0x30,2)
    chunky = number(r['h11']+0x5fc2,4)
    planes = [number(r['h12']+0x42+i*4,4) for i in range(4)]
    colours = bytes(v & 0xf0 for y in range(height) for v in read(chunky+y*192,width))
    planar = b''.join(read(ptr+y*40,width//8) for ptr in planes for y in range(height))
    (a.out/'view.planar').write_bytes(planar)
    (a.out/'view.chunky').write_bytes(colours)
    metadata = dict(anchor='h6:0076c (first call)', width=width, height=height,
                    chunky_sha256=hashlib.sha256(colours).hexdigest(),
                    planar_sha256=hashlib.sha256(planar).hexdigest(),
                    gamefield=number(r['h11']+0x602c,4))
    (a.out/'snapshot.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))
    command('shot', str((a.out/'screen.png').resolve()))
finally:
    if process and process.poll() is None:
        command('quit'); process.wait(timeout=10)
