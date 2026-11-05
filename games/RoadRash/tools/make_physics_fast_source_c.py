from pathlib import Path
from capstone import *
import shutil,re,json
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-physics-fast-source';shutil.copytree(src,dst,dirs_exist_ok=True)
b=(root/'tmp/c-actor-memory-audit/main-field100.bin').read_bytes();lo,hi=0x8b486,0x8d006
cs=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);ins=[]
for a,z in [(lo,0x8c584),(0x8c5a8,0x8ce80),(0x8cef0,hi)]:
 ii=list(cs.disasm(b[a-0x80000:z-0x80000],a));assert sum(x.size for x in ii)==z-a;ins+=ii
fix=[]
for x in ins:
 assert 'pc' not in x.op_str
 m=re.fullmatch(r'\$([0-9a-f]+)',x.op_str)
 if m and x.mnemonic.startswith('b') and not lo<=int(m[1],16)<hi:
  assert x.size==4;fix.append((x.address-lo+2,int(m[1],16)))
entries=[lo,0x8c5a8,0x8c8ae,0x8bbe6,0x8baec,0x8c130,0x8c48e,0x8cef0]
# Internal absolute calls still use native entry points (which may be redirected).
# Copy after C patches so steering hooks retain their canonical native returns.
s='''step_physics_fast_init:
 lea $8b486,a0
 lea step_physics_fast_code(pc),a1
 move.w #7040/4-1,d0
.copy:
 move.l (a0)+,(a1)+
 dbf d0,.copy
 lea step_physics_fast_code(pc),a0
 lea step_physics_fast_fixups(pc),a1
.fix:
 move.w (a1)+,d0
 bmi .patched
 move.w (a1)+,d1
 move.w d1,(a0,d0.w)
 bra .fix
.patched:
 IFD PHYSICS_FAST_CONTROL
 bra.w .done
 ELSE
 nop
 nop
 ENDC
'''
for a in entries:s+=f' lea step_physics_fast_code+${a-lo:x}(pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
s+='''.done:
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
 rts
step_physics_fast_fixups:
'''
for off,t in fix:s+=f' dc.w ${off:x},step_physics_to_{t:x}-(step_physics_fast_code+${off:x})\n'
s+=' dc.w -1\n cnop 0,4\nstep_physics_fast_code:\n ds.b 7040\n'
for t in sorted({t for _,t in fix}):s+=f'step_physics_to_{t:x}:\n jmp ${t:x}\n'
(dst/'physics_fast.s').write_text(s)
p=dst/'RoadRashHD.s';s=p.read_text().replace('.no_c:\n','\tIFD PHYSICS_FAST\n\tbsr step_physics_fast_init\n\tENDC\n.no_c:\n',1);p.write_text(s)
p=dst/'simulation.s';s=p.read_text()+'\n\tIFD PHYSICS_FAST\n\tinclude physics_fast.s\n\tENDC\n';p.write_text(s)
(dst/'manifest.json').write_text(json.dumps(dict(start=lo,end=hi,entries=entries,fixups=fix),indent=2)+'\n')
print('copy bytes',hi-lo,'fixups',len(fix),'entries',len(entries))
