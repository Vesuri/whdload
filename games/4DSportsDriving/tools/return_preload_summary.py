#!/usr/bin/env python3
"""Summarize the differential fully extended suspension fixture; diagnostic only."""
import sys,json,struct
from pathlib import Path
from simulation_fixture import read_fixture
p=Path(sys.argv[1]);rows=[]
for t,h,b in read_fixture(p):
 rows.append(dict(time=t/h,body=list(struct.unpack_from('>iii',b,0x152)),angles=list(struct.unpack_from('>hhh',b,0x16a)),extension=list(struct.unpack_from('>4h',b,0x1a6)),velocity=list(struct.unpack_from('>4h',b,0x19e)),bias=list(struct.unpack_from('>4h',b,0x1be)),cached=list(struct.unpack_from('>12h',b,0x1c6)),surfaces=list(b[0x214:0x218]),crash=b[0x21b]))
assert len(rows)==21 and [r['time'] for r in rows]==[i/10 for i in range(21)]
assert rows[0]['body']==[493824,896,347008] and rows[0]['extension']==[384]*4 and rows[0]['bias']==[0]*4 and rows[0]['velocity']==[0]*4
nonzero=[r['time'] for r in rows if any(r['extension'])]
result=dict(rate=h,rows=rows,last_nonzero_extension=max(nonzero),first_all_zero_extension=next((r['time'] for r in rows if not any(r['extension'])),None),final_y=rows[-1]['body'][1],crash_free=all(not r['crash'] for r in rows),scope='Differential body+384 and all extensions+384 with original native initial cache retained; no claim of fully initialized projected wheel cache or full handling acceptance.')
(p/'return-preload.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));print([(r['time'],r['body'][1],r['extension']) for r in rows if r['time']<=.6])
