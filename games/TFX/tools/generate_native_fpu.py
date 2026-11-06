"""Generate the exhaustive four-byte FPU site table from retained disassembly."""
import json,re,collections
from pathlib import Path
import map_symbols as m
root=m.ROOT;src=root/'src';out=m.ROOT/'tmp/step9';out.mkdir(exist_ok=True)
r=json.loads((m.OUT/'tfx.020-0.json').read_text());code=m.load(m.GAME/'tfx.020')[0]['data']
sites=[];keys=[]
for o,raw,text in r:
 if not text.startswith(('fintrzx ','fmovecrx ')):continue
 b=bytes.fromhex(raw);assert len(b)==4 and code[o:o+4]==b
 if text.startswith('fintrz'):
  a,b=map(int,re.findall(r'fp(\d)',text));key=f'ni_{a}_{b}'
 else:
  c,b=map(int,re.findall(r'\d+',text));assert c in (15,50,52);key=f'nc_{c}_{b}'
 if key not in keys:keys.append(key)
 sites.append(dict(offset=o,original=code[o:o+4].hex(),text=text,key=key))
assert collections.Counter(x['text'].split()[0] for x in sites)=={'fintrzx':146,'fmovecrx':93}
slots={k:0x142+6*i for i,k in enumerate(keys)};assert max(slots.values())+6<0x400
lines=['; Complete tfx.020 FINTRZ/FMOVECR census; generated from disassembly.','; Constants: $0f = 0, $32 = 1, $34 = 100.','native_fpu_patches:','        PL_START','        PL_IFC5','        PL_ELSE']
lines += [f"        PL_L ${x['offset']:x},$4eb80000+${slots[x['key']]:x} ; {x['text']}" for x in sites]
lines += [f'        PL_L ${o:x},$4eb80000+${0x1fc+6*i:x} ; native {n}' for i,(n,o) in enumerate([('tan',0x50f82),('sin',0x5169e),('cos',0x516b6),('atan2',0x517a4),('atan',0x517f2),('asin',0x5183c),('exp',0x51682)])]
lines+=['        PL_ENDIF','        PL_END','','install_native_fpu:']
lines += [f'        patch ${slots[k]:x},{k}' for k in keys]
lines += [f'        patch ${0x1fc+6*i:x},native_{n}' for i,n in enumerate(['tan','sin','cos','atan2','atan','asin','exp'])]
lines+=['        rts','', '        mc68040']
for k in keys:
 kind,a,b=k.split('_');a=int(a);b=int(b)
 if kind=='ni':lines += [f'        NATIVE_INT {a},{b}']
 else:lines += [k+':',f'        fmove.s #{ {15:0,50:1,52:100}[a]},fp{b}','        rts']
lines+=['        mc68020','']
(src/'native_fpu_sites.i').write_bytes(('\r\n'.join(lines)).encode())
(out/'fpu-sites.json').write_text(json.dumps(dict(sites=sites,slots=slots),indent=2))
