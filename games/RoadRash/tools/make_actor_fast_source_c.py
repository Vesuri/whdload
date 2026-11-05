from pathlib import Path
import re,json,shutil
src=Path('src');dst=Path('tmp/c-actor-fast-source');shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text();s=s.replace('dc.l -$5000 ; optional WHDLoad-managed stack and guards','dc.l -$7000 ; diagnostic stack plus separate guarded actor storage')
s=s.replace('\tinclude simulation.s','\tinclude simulation.s\n\tinclude actor_fast.s');p.write_text(s)
p=dst/'simulation.s';s=p.read_text().replace('step_main:\n','step_main:\n\tbsr step_actor_fast_prepare\n',1);p.write_text(s)
refs=[]
for name in ['RoadRashHD.s','simulation.s','steering.s']:
 p=dst/name;lines=[]
 for line in p.read_text().splitlines():
  lines.append(line)
  code=line.split(';')[0]
  values=[int(x,16) for x in re.findall(r'\$([0-9a-fA-F]+)',code)]
  if any(0xa5d60<=v<0xa6ee0 for v in values):
   assert len([v for v in values if 0xa5d60<=v<0xa6ee0])==1,(name,line)
   label='actor_ref_'+str(len(refs));refs.append(label);lines.append(label+' equ *-4')
 p.write_text('\n'.join(lines)+'\n')
audit=json.loads(Path('tmp/c-actor-memory-audit/audit.json').read_text())
native=[(int(a,16),r['value']) for a,r in audit['instruction_operands'].items() if (0x86500<=int(a,16)<0x91000 or 0xb4eac<=int(a,16)<=0xb4f42) and int(a,16)!=0x8a8e8]
assert len(native)==167
code='''; Race-only feasibility diagnostic. Not for release or race transitions.
\tIFND C_RUNTIME_ONLY
\tFAIL "Actor feasibility diagnostic requires the lean runtime"
\tENDC
step_actor_fast_prepare:
\tbra .entry
step_actor_fast_stats:
\tdc.b "RRACTOR1"
\tdc.l 0,0,0,0
.entry:
\tbtst #0,step_actor_fast_stats+11(pc)
\tbne .return
\tcmpi.l #100,$a5d4c
\tbcs .return
\tmove.w sr,-(a7)
\tmove.w #$2700,sr
\tmovem.l d0-d7/a0-a6,-(a7)
\tlea step_actor_fast_prepare(pc),a6
\tadda.l #_base-step_actor_fast_prepare,a6
\tmovea.l _expmem-_base(a6),a5
\tcmpa.l #$200000,a5
\tbcs .failed
\tcmpa.l #$a00000,a5
\tbcs .allocated
\tcmpa.l #$1000000,a5
\tbcs .failed
.allocated:
; Preflight the typed race-code operands before making any change.
\tlea actor_native_refs(pc),a3
.check:
\tmove.l (a3)+,d0
\tbeq .copy
\tmovea.l d0,a0
\tmove.l (a3)+,d1
\tcmp.l (a0),d1
\tbne .failed
\tbra .check
.copy:
\tlea $5000(a5),a0
\tmoveq #3,d0
.guardlo:
\tmove.l #$a55aa55a,(a0)+
\tdbf d0,.guardlo
\tmovea.l a0,a5
\tmovea.l a0,a1
\tlea $a5d60,a0
\tmove.w #$1180/4-1,d0
.copyloop:
\tmove.l (a0)+,(a1)+
\tdbf d0,.copyloop
\tmoveq #3,d0
.guardhi:
\tmove.l #$a55aa55a,(a1)+
\tdbf d0,.guardhi
\tmove.l a5,d7
\tIFD ACTOR_FAST_CONTROL
	sub.l d7,d7
	nop
	nop
	ELSE
	sub.l #$a5d60,d7
	ENDC
\tlea actor_native_refs(pc),a3
.patch:
\tmove.l (a3)+,d0
\tbeq .helpers
\tmovea.l d0,a0
\tmove.l (a3)+,d1
\tadd.l d7,d1
\tmove.l d1,(a0)
\tbra .patch
.helpers:
\tlea actor_helper_refs(pc),a3
.helper:
\tmoveq #0,d0
\tmove.w (a3)+,d0
\tcmpi.w #-1,d0
\tbeq .tables
\tmovea.l a6,a0
\tadda.l d0,a0
\tadd.l d7,(a0)
\tbra .helper
.tables:
\tlea $90948,a0
\tmove.w #($90a10-$90948)/4-1,d6
\tbsr .table
\tlea $94192,a0
\tmove.w #($9422a-$94192)/4-1,d6
\tbsr .table
\tlea $9017c,a0
\tmoveq #0,d6
\tbsr .table
\tlea step_actor_fast_stats(pc),a0
\tmove.l a5,20(a0)
	move.l d7,d0
	add.l #$a5d60,d0
	move.l d0,12(a0)
\tmove.l #167,16(a0)
\tmove.l #3,8(a0)
\tmovea.l _resload-_base(a6),a2
\tjsr (resload_FlushCache,a2)
\tbra .restore
.table:
\tmove.l (a0),d0
\tcmpi.l #$a5d60,d0
\tbcs .next
\tcmpi.l #$a6ee0,d0
\tbcc .next
\tadd.l d7,(a0)
.next:
\taddq.l #4,a0
\tdbf d6,.table
\trts
.failed:
\tlea step_actor_fast_stats(pc),a0
\tmove.l #1,8(a0)
.restore:
\tmovem.l (a7)+,d0-d7/a0-a6
\tmove.w (a7)+,sr
.return:
\trts
actor_native_refs:
'''
code+=''.join(f'\tdc.l ${a:x},${v:x}\n' for a,v in native)+'\tdc.l 0\nactor_helper_refs:\n'
code+=''.join(f'\tIFD {x}\n\tdc.w {x}-_base\n\tENDC\n' for x in refs)+'\tdc.w -1\n'
# Branch above the data needs a global entry label; keep local labels scoped to stats.
code=code.replace('bra .entry','bra step_actor_fast_entry',1).replace('.entry:', 'step_actor_fast_entry:',1)
(dst/'actor_fast.s').write_text(code)
print('generated',len(native),'native references and',len(refs),'conditionally emitted helper references')
