#!/usr/bin/env python3
"""Check ordinary keyboard events through field sampling and native history."""
import argparse,json,re,struct,itertools
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--rate',type=int,choices=(10,20,50),required=True);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text());lst=(a.capture/'slave.lst').read_text(encoding='latin1');sym={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',lst,re.M)}
assert 'sim_fixture_before' not in sym and b'4DSIMFIX' not in b
base=m['marker']+8-sym['tape_game']-m['memory_base'];q=base+sym['tape_live_input_phase'];assert struct.unpack_from('>H',b,q)[0]==3
rows=[struct.unpack_from('>I4H2i',b,q+4+i*20) for i in range(3)]
assert [r[4] for r in rows]==[a.rate]*3,rows
assert [rows[i+1][0]-rows[i][0] for i in range(2)]==[100,100],rows
assert rows[0][3]==0 and rows[1][3]>0 and rows[2][3]>0,rows
assert rows[0][6]<rows[1][6]<rows[2][6],rows
at=m['data_base']+0x7ffe-m['memory_base'];word=lambda o:struct.unpack_from('>H',b,at+o)[0]
assert (word(-0xbc),word(-0x15fa),b[at-0x173a])==(a.rate,)*3
ptr=struct.unpack_from('>I',b,at-0x1770)[0]-m['memory_base'];data=b[ptr:ptr+word(-0x1738)]
runs=[(v,len(list(g))) for v,g in itertools.groupby(data)]
# Native pre-start handling may discard idle zero samples before the first key.
assert [v for v,n in runs] in ([1,0],[0,1,0]),runs
throttle=next(n for v,n in runs if v==1)
assert abs(throttle-a.rate*2)<=1,runs
assert runs[-1][1]>=a.rate,runs
assert struct.unpack_from('>H',b,base+sym['sim_schedule_overflow'])[0]==0
result={'rate':a.rate,'synthetic_fixture':False,'ordinary_key_hold_fields':100,'ordinary_key_release_fields':100,'samples':[dict(zip(('field','produced','consumed','speed','rate','x','z'),r)) for r in rows],'native_history_runs':runs,'queue_overflow':False}
(a.capture/'live-input-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
