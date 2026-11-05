from pathlib import Path
import sys,json,struct,hashlib
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games/FerrariFormulaOne';sys.path.insert(0,str(g));from native import catalog
from capstone import *
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020)
layout=json.loads((g/'layout.json').read_text());game=r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu';refs=[]
for group in catalog(game):
 for h in group['hunks']:
  for dest,offs in h['reloc'].items():
   for off in offs:
    if dest!=4:continue
    val=struct.unpack_from('>I',h['data'],off)[0]+layout['4']['base']
    if val!=0x1c1b8:continue
    at=max(0,off-2);raw=h['data'][at:off+16]
    refs.append(dict(group=hex(group['header']),hunk=h['number'],operand=hex(off),target=hex(val),bytes=raw.hex(),disassembly=[f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in c.disasm(raw,at)]))
old=json.loads((r/'manifest/step5-c4-r2-scratch-relocations.json').read_text());prior=[x for x in old['references'] if x['target']=='0x1c1b8'];assert {(x['group'],x['hunk'],x['operand']) for x in prior}=={(x['group'],x['hunk'],x['operand']) for x in refs};assert len(refs)==5
result=dict(status='passed',game_sha256=hashlib.sha256(game.read_bytes()).hexdigest(),references=refs,prior_alias_review=old['audit_notes']);(r/'manifest/render-h2-scratch.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
