#!/usr/bin/env python3
"""Validate sampled KickEmu FastMem lists on the anchored private040 setup."""
import argparse,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('snapshots',nargs='+');p.add_argument('--header',type=lambda s:int(s,0),default=0x51f4c2);a=p.parse_args();m=json.loads((a.capture/'start/anchor.json').read_text());result={}
for name in a.snapshots:
 b=(a.capture/(name+'.bin')).read_bytes();rd=lambda addr:struct.unpack_from('>I',b,addr-m['memory_base'])[0]
 assert b[a.header+8-m['memory_base']]==10
 n,lo,hi,free=struct.unpack_from('>4I',b,a.header+16-m['memory_base']);assert m['memory_base']<=lo<hi<=m['memory_base']+len(b)
 total=0;end=lo;nodes=[]
 while n:
  assert end<=n<hi and n%8==0,(name,hex(n));link,size=rd(n),rd(n+4);assert size>=8 and size%8==0 and n+size<=hi,(name,hex(n),size)
  total+=size;nodes.append([hex(n),size]);end=n+size;n=link
 assert total==free,(name,total,free);result[name]=dict(header=hex(a.header),bounds=[hex(lo),hex(hi)],free_bytes=free,chunks=nodes)
(a.capture/'heap-validation.json').write_text(json.dumps(result,indent=2)+'\n');print('Valid sampled free lists:',', '.join(result))
