#!/usr/bin/env python3
"""Phase 1 boot/code/overlay evidence, no performance measurement or game writes."""
import argparse, hashlib, json, os, shutil, struct, time
from pathlib import Path
from gpc import server, ROOT
from gpc_report import regions
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--hunk',type=lambda x:int(x,0),default=0xd00210);p.add_argument('--cycles',type=int,default=2);p.add_argument('--calibrate',action='store_true');a=p.parse_args()
out=Path('tmp/validation')/a.name;out.mkdir(parents=True,exist_ok=True)
selected=Path(os.environ.get('SLAVE') or Path(ROOT)/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/GrandPrixCircuit.Slave')
shutil.copyfile(selected,out/'slave.slave')
(out/'slave.sha256').write_text(hashlib.sha256(selected.read_bytes()).hexdigest()+'\n')
base=int(os.environ.get('DUMP_BASE','0xc00000'),0);size=int(os.environ.get('DUMP_SIZE','0x180000'),0)
log=[]
def cmd(text,timeout=120):
    result=g.cmd(text,timeout=timeout);log.append(text+'\n'+result);(out/'debugger.txt').write_text('\n'.join(log));return result

def dump(name):
    cmd(f'dump binary memory {out}/{name}.bin {base:#x} {base+size:#x}')
    return (out/f'{name}.bin').read_bytes()

def shot(name):
    server.handle(g,f'shot {out}/{name}.png')

def stop_at(addr):
    result=cmd('continue',timeout=180)
    pc=int(cmd('p/x $pc').split('=')[-1].strip(),16)
    assert pc==addr, f'unexpected stop {pc:#x}: {result}'

try:
    g=server.boot()
    if a.calibrate:
        g.cont(); time.sleep(5);g.stop();d=dump('calibration')
        rr={n:lo for lo,hi,n,o in regions(d,base)}
        print({k:hex(v) for k,v in rr.items()},flush=True);shot('calibration');raise SystemExit(0)
    hb=a.hunk
    cmd(f'break *{hb+0x18:#x}');stop_at(hb+0x18);cmd('delete')
    d=dump('entry');rr={n:lo for lo,hi,n,o in regions(d,base)}
    assert rr['gpc']==hb
    db=rr['gpc-data'];table=d[db-base:db-base+0x342]
    for off in (0xd42c,0xd43e,0xd4a2):cmd(f'break *{hb+off:#x}')
    # A watch over all 139 six-byte jump stubs; hardware stub range, no game writes.
    watch=cmd(f'watch -location *(char (*)[834]){db:#x}')
    assert 'watchpoint' in watch.lower(),watch
    # Main's first return from the intro displays the menu / attract transition.
    cmd(f'break *{hb+0x4d94:#x}');stop_at(hb+0x4d94);cmd('delete $bpnum');shot('title');dump('title')
    for n in range(a.cycles):
        cmd(f'break *{hb+0x7094:#x}');stop_at(hb+0x7094);cmd('delete $bpnum')
        # A first complete game draw, then enough draws to observe movement.
        cmd(f'break *{hb+0x39e:#x}')
        for k in range(40):stop_at(hb+0x39e)
        cmd('delete $bpnum');shot(f'race{n}')
        d=dump(f'race{n}');assert d[db-base:db-base+0x342]==table,'jump table changed'
        if n+1<a.cycles:
            cmd(f'break *{hb+0xf8:#x}');stop_at(hb+0xf8);cmd('delete $bpnum');shot('intro-return')
    cmd('info breakpoints')
    # Positive control: the same-size watch must catch a native VBL counter write.
    cmd('delete')
    cmd(f'watch -location *(char (*)[834]){db+0x3d0:#x}')
    hit=cmd('continue')
    assert 'Hardware watchpoint' in hit, 'watchpoint positive control failed'
    print('834-byte watchpoint positive control: native VBL write caught',flush=True)
    (out/'metadata.json').write_text(json.dumps(dict(code_base=hb,data_base=db,base=base,table_bytes=len(table),overlay_hits=0,slave=os.environ.get('SLAVE','shipped'),custom2=0),indent=2))
    print(f'{a.name}: intro, {a.cycles} demo entries, 139 stubs unchanged, no overlay entry/write/watchpoint hits',flush=True)
finally:
    (out/'debugger.txt').write_text('\n'.join(log))
    if server.g is not None: server.handle(server.g,'quit')
