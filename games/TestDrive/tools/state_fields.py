#!/usr/bin/env python3
"""Capture TD data at successive Ticks VBLInt counter stores, without target writes."""
import argparse,json,re,shutil
from pathlib import Path
from td import server
from td_report import regions,game_bytes
from harness import ROOT,command,output,sha,machine_config
from state_report import DATA_SIZE,value,VARIABLES
VBL=0x18ba

def capture(fields,out,dump,base,skip=0):
    if not 1<=fields<=9999 or skip<0:raise ValueError('invalid field count')
    out=Path(out).resolve();output(out/'metadata.json')
    if (out/'metadata.json').exists():raise ValueError('capture already exists')
    rr={n:lo for lo,hi,n,o in regions(Path(dump).read_bytes(),base)};hb,db=rr['td'],rr['td-data'];vbl=hb+VBL
    server.request('stop');r=command('info registers pc')
    if not re.search(r'pc\s+'+hex(vbl)+r'\b',r):
        r=server.request(f'until {vbl:#x}')
        if f'{vbl:08x}' not in r.lower():raise RuntimeError(r)
    guard=command(f'printf "TD_CONTEXT_OK=%d\\n", ($a4 == {db+0x7ffe:#x} && $a1 == {db+0x3d8:#x})')
    if 'TD_CONTEXT_OK=1' not in guard:raise RuntimeError('VBL context does not match TD data hunk: '+guard)
    command('cd '+str(ROOT))
    rel=out.relative_to(ROOT)
    lines=[f'break *{vbl:#x}', 'set $td_sample = 0']
    if skip:lines += [f'set $td_skip = {skip}','while $td_skip > 0','continue','set $td_skip = $td_skip - 1','end']
    lines += [f'while $td_sample < {fields}',f'eval "dump binary memory {rel}/%04d.bin {db:#x} {db+DATA_SIZE:#x}", $td_sample','set $td_sample = $td_sample + 1',f'if $td_sample < {fields}','continue','end','end','delete']
    (out/'gdb.txt').write_text(command('\n'.join(lines)))
    data=[(out/f'{i:04d}.bin').read_bytes() for i in range(fields)]
    ticks=[value(b,*VARIABLES['vbl']) for b in data]
    if any((y-x)&0xffffffff!=1 for x,y in zip(ticks,ticks[1:])):raise RuntimeError('samples are not successive VBL entries')
    shutil.copyfile(out/'0000.bin',out/'initial.bin')
    config=machine_config()
    machine={k:config[k] for k in ('amiga_model','cpu','chip_memory','fast_memory','slow_memory','uae_cpu_frequency','uae_cpu_cycle_exact','ntsc_mode','deterministic') if k in config}
    import hashlib
    m=dict(game='TD',data_size=DATA_SIZE,code_base=hb,data_base=db,a4=db+0x7ffe,fields=fields,skip_fields=skip,anchor='td:018ba before counter increment',vbl_first=ticks[0],slave_sha256=sha(ROOT/'tmp/run/default/.run/dh1/TestDrive.slave'),game_sha256=hashlib.sha256(game_bytes()).hexdigest(),machine=machine)
    (out/'metadata.json').write_text(json.dumps(m,indent=2)+'\n');return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('fields',type=int);p.add_argument('out');p.add_argument('dump');p.add_argument('base',type=lambda x:int(x,0));p.add_argument('--skip',type=int,default=0);a=p.parse_args()
    print(json.dumps(capture(a.fields,a.out,a.dump,a.base,a.skip),indent=2))
if __name__=='__main__':main()
