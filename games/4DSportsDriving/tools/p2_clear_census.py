import json,re,struct
from pathlib import Path
from profile_window import command
import sys
cap=Path(sys.argv[1]);meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base']
command('stop');command('gdb delete');rows=[]
for _ in range(12):
 command(f'gdb tbreak *{g+0x347b0:#x}\ncontinue')
 regs={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
 assert regs['pc']==g+0x347b0
 rows.append({k:regs[k] for k in ['d0','d1','d2','d3','d4','d5','d7','a0','a2']})
(cap/'clear-census.json').write_text(json.dumps(rows,indent=2)+'\n')
print(rows)
