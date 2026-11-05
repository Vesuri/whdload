#!/usr/bin/env python3
"""Read the optional VERIFY swap/first-fill ring without advancing emulation."""
import argparse,json,struct
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
r.locate();data=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();base=r.DUMP_BASE;matches=[];start=0
while (i:=data.find(b'RBPAINT1',start))>=0:
 h=struct.unpack_from('>14I',data,i+8)
 if h[0]==1:h=(*h[:12],0,0)
 if h[0] in (1,2) and h[1:3]==(40,256) and base<=h[4]<base+len(data):matches.append((base+i,h))
 start=i+8
if len(matches)!=1:raise RuntimeError(f'Expected one active paint observer: {matches}')
at,h=matches[0];version,stride,capacity,count,buffer,policy,pending,missed,sv,sb,new,old,cacr,cacr_valid=h
r.command(f'gdb dump binary memory tmp/build/paint.bin {buffer:#x} {buffer+stride*capacity:#x}')
raw=(r.ROOT/'tmp/build/paint.bin').read_bytes();rows=[]
names=['step','swap_vbl','swap_beam','draw_vbl','draw_beam','destination','old_display','new_display','bltsize','reserved','ticks']
for n in range(max(0,count-capacity),count):
 row=dict(zip(names,struct.unpack_from('>8I2HI',raw,n%capacity*stride)))
 if not row['old_display']<=row['destination']<row['old_display']+40000:raise RuntimeError('Destination outside recorded old display')
 row['swap_line']=(row['swap_beam']>>8)&511;row['draw_line']=(row['draw_beam']>>8)&511
 row['potential_active_old_display']=row['swap_vbl']==row['draw_vbl'] and 42<=row['swap_line']<=row['draw_line']<=243
 rows.append(row)
result=dict(header=at,version=version,count=count,cache_policy=policy,raw_cacr=cacr,cacr_valid=bool(cacr_valid),policy_instruction_cache=bool(policy&256),policy_data_cache=bool(policy&512),pending=pending,missed=missed,records=rows)
a.out.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='records'});print('potential active old-display fills',sum(x['potential_active_old_display'] for x in rows))
