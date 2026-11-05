"""Check the rotation model against the original renderer's actual trace calls."""
import sys,json
from pathlib import Path
import numpy as np
import barto_mmap as barto
out=Path(sys.argv[1]);meta=json.loads((out/'metadata.json').read_text());base=meta['layout']['code_base'];t=barto.load(out/'trace.bin');pending={};tested={'y':0,'x':0};special=0
for f in t.fields:
 assert (f.insn_end-f.insn_off)%76==0
 rows=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19)
 offs=rows[:,0].astype(np.int64)-base
 for row in rows[np.isin(offs,[0x2a50,0x2a68,0x2a9c,0x2ab4])]:
  pc=int(row[0])-base;r=list(map(int,row[2:]));axis='y' if pc<0x2a7a else 'x'
  if pc in [0x2a50,0x2a9c]:
   vals=[v&65535 for v in [r[4],r[5],r[1],r[2]]];x,z,c,s=[v-65536 if v&32768 else v for v in vals];pending[axis]=((((x*c-z*s)&0xffffffff)>>14)&65535,(((z*c+x*s)&0xffffffff)>>14)&65535)
   if c==0 or s==0:special+=1
  elif axis in pending:
   got=(r[7]&65535,r[5]&65535);assert got==pending.pop(axis),(f.index,hex(pc),got);tested[axis]+=1
report=dict(passed=True,vertices=tested,zero_coefficient_vertices=special,scope='Independent signed-word rotation model versus native input/output registers in retained gameplay trace',slave_sha256=meta['slave_sha256']);(out/'rotation-model.json').write_text(json.dumps(report,indent=2)+'\n');print(out.name,report)
