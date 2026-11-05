from pathlib import Path
import bisect,collections,json,re,sys
import barto_mmap as b
from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
p=Path('tmp/prof')/sys.argv[1];m=json.loads((p/'metadata.json').read_text());s={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]+) (_\w+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['layout']['published']-s['_code_start'];t=b.load(p/'trace.bin');order=sorted((v,k) for k,v in s.items());addresses=[v for v,k in order];end=base+(p/'slave.slave').stat().st_size
cost=collections.Counter();calls=collections.Counter();owners={}
for f in t.fields:
 for pc,c,r in t.instructions(f):
  if pc and base<=pc<end:
   if pc not in owners:owners[pc]=order[bisect.bisect_right(addresses,pc-base)-1][1]
   if owners[pc].startswith(('_phase','_time','_motion','_projection','_contact','_drivetrain')):cost[pc]+=c;calls[pc]+=1
image=(p/'anchor-slow.bin').read_bytes();cs=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);rows=[]
for pc,v in cost.most_common(80):
 ins=next(cs.disasm(image[pc-0xc00000:pc-0xc00000+16],pc),None)
 rows.append(dict(symbol=owners[pc],offset=pc-base-s[owners[pc]],cycles=v,calls=calls[pc],mean_cost=v/calls[pc],insn=(ins.mnemonic+' '+ins.op_str) if ins else '?'))
(p/'instruction-costs.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows[:50]:print(row)
