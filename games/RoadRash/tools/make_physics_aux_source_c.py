from pathlib import Path
from capstone import *
import shutil,re,json
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-physics-aux-source';shutil.copytree(src,dst,dirs_exist_ok=True)
b=(root/'tmp/c-actor-memory-audit/main-field100.bin').read_bytes();cs=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020)
ranges=[(0x8d2c0,0x8d8d0),(0x8dd66,0x8de6c),(0x8e166,0x8e2d6),(0x8da5c,0x8db0a)];entries=[0x8d2c0,0x8d40a,0x8d46e,0x8d4e6,0x8dd66,0x8e166,0x8e252,0x8da5c]
def target(t):
 for a,z in ranges:
  if a<=t<z:return f'aux_{a:x}+${t-a:x}'
 return f'aux_to_{t:x}'
fix=[];external=set();s='''step_physics_aux_init:
'''
for a,z in ranges:s+=f''' lea ${a:x},a0
 lea aux_{a:x}(pc),a1
 move.w #{(z-a)//2-1},d0
.copy_{a:x}:
 move.w (a0)+,(a1)+
 dbf d0,.copy_{a:x}
'''
for a,z in ranges:
 ii=list(cs.disasm(b[a-0x80000:z-0x80000],a));assert sum(x.size for x in ii)==z-a
 for x in ii:
  assert 'pc' not in x.op_str
  m=re.fullmatch(r'\$([0-9a-f]+)',x.op_str)
  if m and x.mnemonic.startswith('b') and not a<=int(m[1],16)<z:
   assert x.size==4,(hex(x.address),x.mnemonic);t=int(m[1],16);off=x.address-a+2;label=target(t)
   if label.startswith('aux_to'):external.add(t)
   fix.append([a,off,t]);s+=f' lea aux_{a:x}(pc),a0\n move.w #{label}-(aux_{a:x}+${off:x}),${off:x}(a0)\n'
s+=' IFD PHYSICS_AUX_CONTROL\n bra.w .done\n ELSE\n nop\n nop\n ENDC\n'
for t in entries:s+=f' lea {target(t)}(pc),a0\n move.w #$4ef9,${t:x}\n move.l a0,${t+2:x}\n'
s+='''.done:
 lea step_physics_aux_init(pc),a2
 suba.l #step_physics_aux_init-_resload,a2
 move.l (a2),a2
 jsr (resload_FlushCache,a2)
 rts
'''
for a,z in ranges:s+=f' cnop 0,2\naux_{a:x}:\n ds.b {z-a}\n jmp ${z:x}\n'
for t in sorted(external):s+=f'aux_to_{t:x}:\n jmp ${t:x}\n'
(dst/'physics_aux.s').write_text(s)
p=dst/'RoadRashHD.s';s=p.read_text().replace('.no_c:\n','\tIFD PHYSICS_AUX\n\tlea _base(pc),a0\n\tadda.l #step_physics_aux_init-_base,a0\n\tjsr (a0)\n\tENDC\n.no_c:\n',1);p.write_text(s)
p=dst/'simulation.s';p.write_text(p.read_text()+'\n\tIFD PHYSICS_AUX\n\tinclude physics_aux.s\n\tENDC\n')
p=dst/'physics_fast.s';s=p.read_text()
for t in [0x8da5c,0x8e166]:
 old=f'step_physics_to_{t:x}:\n jmp ${t:x}\n';new=f'step_physics_to_{t:x}:\n IFD PHYSICS_AUX\n IFND PHYSICS_AUX_CONTROL\n jmp {target(t)}(pc)\n nop\n ELSE\n jmp ${t:x}\n ENDC\n ELSE\n jmp ${t:x}\n ENDC\n';assert old in s;s=s.replace(old,new)
p.write_text(s);(dst/'manifest.json').write_text(json.dumps(dict(ranges=ranges,entries=entries,fixups=fix),indent=2)+'\n');print('bytes',sum(z-a for a,z in ranges),'fixups',len(fix),'external targets',len(external))
