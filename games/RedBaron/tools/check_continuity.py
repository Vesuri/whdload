#!/usr/bin/env python3
"""Measure requested versus actually elapsed fields using the VERIFY VBlank observer."""
import argparse,json,re,time
from pathlib import Path
import step_log,route_status as r
from profile_flight import command
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
at,h=step_log.header();vbl=at+36;sim=h[6]
def readword(addr):
    txt=r.command(f'gdb x/wx {addr:#x}')
    return int(re.findall(r':\s*(0x[0-9a-f]+)',txt)[-1],16)
rows=[]
for n in [20,10,10,1,1,1]:
    before=readword(vbl);tick0=readword(sim+0x30006)
    target=out/f'capture-{len(rows)}-{n}.bin'
    command(f'profile {n} {target}')
    after=readword(vbl);tick1=readword(sim+0x30006)
    row=dict(requested=n,vbl_before=before,vbl_after=after,elapsed_fields=after-before,ticks=tick1-tick0,file=target.name)
    rows.append(row);print(json.dumps(row),flush=True)
(out/'continuity.json').write_text(json.dumps(rows,indent=2)+'\n')
