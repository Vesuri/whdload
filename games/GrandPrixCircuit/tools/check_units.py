#!/usr/bin/env python3
"""Check only Phase 1 VERIFY discovery metadata. No rate helpers exist yet."""
import argparse,struct
from pathlib import Path
from gpc_report import regions
p=argparse.ArgumentParser();p.add_argument('dump',type=Path);p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000);a=p.parse_args()
b=a.dump.read_bytes();r={n:lo for lo,hi,n,o in regions(b,a.base)}
hits=[];start=0
while (i:=b.find(b'GPCVERIFY\0',start))>=0:
    h,v=struct.unpack_from('>II',b,i+10);start=i+1
    if h==r['gpc'] and v==1:hits.append(i)
assert len(hits)==1,'VERIFY v1 discovery record missing or ambiguous'
print('VERIFY: v1 PatchSeg path selected; live hunk pointer correct (no rate unit tests in Phase 1)')
