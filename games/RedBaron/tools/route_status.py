#!/usr/bin/env python3
"""Read the live VERIFY marker; optionally wait for a minimum emitted-key count."""
import argparse,json,re,socket,struct,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def command(text):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(650);s.connect(str(ROOT/'tmp/run/default/.run/redbaron.sock'));s.sendall(text.encode());data=b''
        while True:
            chunk=s.recv(65536)
            if not chunk:break
            data+=chunk
    result=data.decode()
    if 'ERROR' in result:raise RuntimeError(result)
    return result
DUMP_BASE=0x200000
def memory_regions():
    cfg=ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/debug.uae'
    values=dict(re.findall(r'^(\w+)=(-?\d+)$',cfg.read_text(),re.M)) if cfg.exists() else {}
    fast=int(values.get('fastmem_size','2'))*0x100000
    slow=int(values.get('bogomem_size','2'))*0x40000
    chip=int(values.get('chipmem_size','2'))*0x80000
    z3=int(values.get('z3mem_size','0'))*0x100000
    log=ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/fs-uae.log.txt'
    actual=re.findall(r'Card \d+: Z3 (0x[0-9A-Fa-f]+)\s+\d+M RAM',log.read_text(errors='replace')) if log.exists() else []
    z3base=int(actual[-1],16) if actual else 0x40000000
    return [(base,base+size) for base,size in [(0x200000,fast),(0xc00000,slow),(0,chip),(z3base,z3)] if size>0]
def locate():
    global DUMP_BASE
    for base,end in memory_regions():
        command(f'gdb dump binary memory tmp/build/route-ram.bin {base:#x} {end:#x}')
        b=(ROOT/'tmp/build/route-ram.bin').read_bytes();start=0;matches=[]
        while True:
            i=b.find(b'RBVERIFY',start)
            if i<0:break
            v=struct.unpack_from('>9I',b,i+8)
            if base<=v[0]<end and base<=v[7]<end:matches.append(base+i)
            start=i+8
        if len(matches)>1:raise RuntimeError(f'Ambiguous live marker: {matches}')
        if matches:
            DUMP_BASE=base
            return matches[0]
    raise RuntimeError('Live marker not found in configured RAM banks')

def read(at):
    raw=command(f'gdb x/12wx {at+8:#x}')
    words=[]
    for line in raw.splitlines():
        if re.match(r'^0x[0-9a-f]+:',line):words += [int(x,16) for x in re.findall(r'0x[0-9a-f]+',line.split(':',1)[1])]
    if len(words)!=12:raise RuntimeError(raw)
    return dict(zip(['menu_hook','emit_hook','baron','ps','sim','polls','events','anchor','control_calls','game_steps','game_anchor','inflight'],words))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--events',type=int,default=0);p.add_argument('--timeout',type=float,default=60);p.add_argument('--shot');a=p.parse_args()
    deadline=time.monotonic()+a.timeout;at=locate()
    while True:
        state=read(at)
        if state['events']>=a.events:break
        if time.monotonic()>deadline:raise SystemExit(f'Timed out: {state}')
        time.sleep(1)
    print(json.dumps(dict(marker=at,**state),indent=2))
    if a.shot:print(command('shot '+str((ROOT/a.shot).resolve())))
