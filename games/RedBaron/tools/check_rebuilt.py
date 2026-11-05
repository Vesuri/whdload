#!/usr/bin/env python3
"""Tapeless shipped/rebuilt opening check at the 1001st native PS keyboard poll + 100 fields.
Each slave gets a calibration boot to discover its relocated poll address, followed by a
fresh boot with that read-only breakpoint armed at CPU reset. No game input is injected.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import route_status as r,barto
ROOT=Path(__file__).resolve().parents[1]
def start(slave,out,anchor=None):
    try:r.command('quit')
    except (OSError,RuntimeError):pass
    env=dict(os.environ,SLAVE=str(slave),WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing',JOY1='none')
    env.pop('BOOT_BREAK',None)
    if anchor:env['BOOT_BREAK']=hex(anchor)
    with (out/'serve.log').open('w') as f:
        server=subprocess.Popen([sys.executable,'tools/redbaron.py','serve'],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    deadline=time.monotonic()+240
    while True:
        if server.poll() is not None:raise RuntimeError((out/'serve.log').read_text())
        if 'serving on' in (out/'serve.log').read_text():return server
        if time.monotonic()>deadline:raise TimeoutError('No debugger server')
        time.sleep(.5)
def find_ps():
    r.command('gdb dump binary memory tmp/build/equivalence-ram.bin 0x200000 0x400000')
    b=(ROOT/'tmp/build/equivalence-ram.bin').read_bytes()
    original=(ROOT/'tmp/game/RedBaron/data/ps').read_bytes()
    needle=original[0x30:0x3c];start=0
    while (i:=b.find(needle,start))>=0:
        base=0x200000+i
        if b[i+0x15b3a:i+0x15b40]==b'\x4e\xf9'+(base+0x2b4f4).to_bytes(4,'big'):return base
        start=i+2
    return None
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--rebuilt',type=Path,default=ROOT/'tmp/build/RedBaron.slave');a=p.parse_args();os.chdir(ROOT);out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
results=[]
for label,slave in [('shipped',ROOT/'tmp/game/RedBaron/RedBaron.slave'),('rebuilt',a.rebuilt.resolve())]:
    target=out/label;target.mkdir();cal=target/'calibration';cal.mkdir();start(slave,cal)
    deadline=time.monotonic()+120
    while not (ps:=find_ps()):
        if time.monotonic()>deadline:raise TimeoutError('PS segment not found')
        time.sleep(.5)
    r.command('stop');start(slave,target,ps+0x15b3a)
    print(r.command(f'gdb break *{ps+0x15b3a:#x}\nignore $bpnum 999\ncontinue\ndelete'),flush=True)
    rel=target.relative_to(ROOT)
    if any(c.isspace() for c in str(rel)):raise ValueError('No whitespace in relative output')
    # Direct monitor capture: PCs are unnecessary for pixel/RAM equivalence, no LLDB needed.
    print(r.command(f'gdb monitor profile 100 "" "{target}/opening.bin"'),flush=True)
    r.command(f'gdb dump binary memory {rel}/after-chip.bin 0 0x100000')
    r.command(f'gdb dump binary memory {rel}/after-fast.bin 0x200000 0x400000')
    (target/'slave.slave').write_bytes(slave.read_bytes())
    t=barto.load(target/'opening.bin');(target/'opening.png').write_bytes(t.fields[-1].shot);(target/'chip.bin').write_bytes(t.chip)
    results.append(dict(label=label,ps=ps,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),screenshot_sha256=hashlib.sha256(t.fields[-1].shot).hexdigest()))
    print(results[-1],flush=True)
l=(out/'shipped/chip.bin').read_bytes();rr=(out/'rebuilt/chip.bin').read_bytes()
summary=dict(runs=results,same_screenshot=results[0]['screenshot_sha256']==results[1]['screenshot_sha256'],chip_bytes_different=sum(a!=b for a,b in zip(l,rr)),chip_sizes=[len(l),len(rr)])
(out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
