#!/usr/bin/env python3
"""Independent exact-time oracle for helpers and original native row calls."""
import argparse,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--rows',action='store_true');a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();meta=json.loads((a.capture/'anchor.json').read_text())
sym={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
pos=b.index(b'4DSCFMT!');assert struct.unpack_from('>HHI',b,pos+8)==(1,39,39)
base=pos+12-sym['sim_score_display_passed']
for n,v in [('sim_score_display_buffer_guard',0x11223344),('sim_score_display_buffer_end',0x55667788)]:assert struct.unpack_from('>I',b,base+sym[n])[0]==v
result={'selftests':39,'guards':'intact'}
if a.rows:
 pos=base+sym['sim_score_display_native_count'];assert struct.unpack_from('>I',b,pos)[0]==1
 rows=base+sym['sim_score_display_rows'];assert struct.unpack_from('>I',b,rows+644)[0]==0x524f5753
 exact=struct.unpack_from('>7Q',b,base+sym['sim_score_records'])
 idx=struct.unpack_from('>7H',b,meta['data_base']+0x7ffe-0x160a-meta['memory_base'])
 values=[]
 for i,k in enumerate(idx):
  at=rows+i*92;before=struct.unpack_from('>H',b,at)[0];after=struct.unpack_from('>H',b,at+6)[0]
  assert before==after==meta['active_simulation_word'],(before,after)
  off=b[at+5];assert off<84,off
  text=b[at+8+off:at+92].split(b'\0',1)[0].decode()
  value=exact[k];value=0 if value==0xffffffffffffffff else value
  minutes,rem=divmod(value,6000);seconds,cents=divmod(rem,100);expected=f'{minutes:2d}:{seconds:02d}.{cents:02d}'
  assert text==expected,(i,k,text,expected,off)
  values.append(text)
 result.update(native_rows=values,index_map=idx,mode_preserved=before)
(a.capture/'score-display-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
