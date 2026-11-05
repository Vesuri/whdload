from pathlib import Path
import sys,struct,json,hashlib
from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
sys.path.insert(0,str(Path(__file__).parent));from overlay_map import catalog,decode
r=Path(__file__).resolve().parents[1];out=r/'tmp/step4';out.mkdir(exist_ok=True)
m=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);m.skipdata=True
refs=[]
for gr in catalog():
 for h in gr['hunks']:
  rel={o:(target,struct.unpack_from('>I',h['data'],o)[0]) for target,offsets in h['reloc'].items() for o in offsets}
  for o,(target,v) in rel.items():
   if (target==9 and v in (0,0x6e,0xc0,0x372)) or (target==32 and v==0x1a):refs.append({'header':gr['identity'],'hunk':h['number'],'offset':hex(o),'target_hunk':target,'target_offset':hex(v)})
  if h['type']!='HUNK_CODE':continue
  lines=[]
  for i in m.disasm(h['data'],0):
   labels=[f'h{t}+${v:x}' for o,(t,v) in rel.items() if i.address<=o<i.address+len(i.bytes)]
   lines.append(f'{i.address:04x}: {i.mnemonic} {i.op_str}'+(' ; '+', '.join(labels) if labels else ''))
  (out/f'{gr["header"]:x}-h{h["number"]}.dis').write_text('\n'.join(lines)+'\n')
b=(r/'tmp/step3/a500-c0-a/anchor.bin').read_bytes();lines=[];mapping=decode(b)
for gr in mapping['groups']:
 for h in gr['hunks']:
  if h['type']!='HUNK_CODE':continue
  for i in m.disasm(b[h['base']:h['base']+h['size']],h['base']):lines.append(f'{i.address:06x}: {i.bytes.hex():20} {i.mnemonic} {i.op_str} ; {gr["identity"]} h{h["number"]}+{i.address-h["base"]:x}')
(out/'active.dis').write_text('\n'.join(lines)+'\n')
(r/'manifest/step4-clock-refs.json').write_text(json.dumps(refs,indent=2)+'\n')
raw=(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu').read_bytes()
weights=next(h['base'] for gr in mapping['groups'] for h in gr['hunks'] if h['number']==10)
result={'executable_sha256':hashlib.sha256(raw).hexdigest(),'calendar_tenth_weights':struct.unpack_from('>10i',b,weights),'device_string_file_offsets':{s.decode():raw.find(s) for s in (b'timer.device',b'audio.device',b'keyboard.device')},'field_counter_refs':[v for v in refs if v['target_hunk']==32],'limits':'Relocation references and decoded instructions aid a scoped manual audit; no blanket proof about all indirect pointers or OS internals.'}
(r/'manifest/step4-static-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Clock and overlay audit saved')
