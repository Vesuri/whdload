import json,re,sys
from pathlib import Path
import numpy as np
import barto_mmap as barto
from machine_profiles import banks
from capstone import *
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());lst=(p/'slave.lst').read_text(encoding='latin1');sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',lst,re.M)[1],16);slave=m['layout']['published']-sym('_code_start');name='_render_wait' if m['render_window']['custom3']&4 else '_blitwait';start=slave+sym(name);memory=[(b,(p/('anchor-'+n+'.bin')).read_bytes()) for n,b,z in banks(m['configuration'])];data=next(b[start-a:start-a+256] for a,b in memory if a<=start< a+len(b));md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);end=next(i.address for i in md.disasm(data,start) if i.mnemonic=='rts');t=barto.load(p/'trace.bin');before=None;cases=0
for f in t.fields:
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19)
 for r in a[(a[:,0]==start)|(a[:,0]==end)]:
  if r[0]==start:before=r[2:].copy()
  elif before is not None:
   after=r[2:];assert np.array_equal(before[:16],after[:16]),(cases,'registers');cases+=1;before=None
assert cases>100
result=dict(passed=True,completed_calls=cases,helper=name,scope='Actual DMA/gameplay calls preserve D0-D7/A0-A7. The profiler copies raw regs.sr without MakeSR, so it cannot verify CCR. Materialized flags and busy transitions are separately checked by the independent Python/original/replacement contract.');(p/'wait-contract.json').write_text(json.dumps(result,indent=2)+'\n');print(p.name,result)
