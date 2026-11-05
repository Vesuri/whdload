from pathlib import Path
r=Path(__file__).resolve().parents[1]
# Direct calls to the installed, relocated clock wrapper, with native clock
# storage and mode fields restored before driving resumes.
times=[(0,0,0,0,0,0,0),(0,0,0,0,5,9,9),(0,3,5,9,5,9,9),(0,4,5,8,5,9,8),(0,4,5,8,5,9,9)]
weights=(360000,36000,6000,600,100,10,1)
def digits(n):
 out=[]
 for w in weights:out.append(n//w);n%=w
 return out
asm='''C4TestClocks:
 lea C4ClockSaved(pc),a0
 lea $226c0,a1
 moveq #4,d0
.save:
 move.l (a1)+,(a0)+
 dbra d0,.save
 move.w $1ed2c,(a0)+
 move.w $1c222,(a0)
'''
cases=[]
for ptr in (0x226c0,0x226ca):
 for mode,flag in [(12,0),(12,1),(0,0)]:
  for t in times:
   n=sum(a*b for a,b in zip(t,weights))+1
   if not(ptr==0x226c0 and mode==12 and flag==0 and digits(n)[1:4]==[4,5,9]):n+=1
   expected=digits(n);cases.append(dict(pointer=hex(ptr),mode=mode,flag=flag,start=t,expected=expected));i=len(cases)
   asm+=f' move.w #{mode},$1ed2c\n move.w #{flag},$1c222\n'
   for off,v in enumerate(t,3):asm+=f' move.b #{v},${ptr+off:x}\n'
   asm+=f' pea ${ptr:x}\n bsr.w FF1ClockTick\n addq.l #4,sp\n'
   for off,v in enumerate(expected,3):asm+=f' cmpi.b #{v},${ptr+off:x}\n bne.w C4ClockBad{i}\n'
   asm+=' lea C4ClockChecked(pc),a0\n addq.l #1,(a0)\n'
asm+=''' lea C4ClockSaved(pc),a0
 lea $226c0,a1
 moveq #4,d0
.restore:
 move.l (a0)+,(a1)+
 dbra d0,.restore
 move.w (a0)+,$1ed2c
 move.w (a0),$1c222
 rts
'''
for i in range(1,len(cases)+1):asm+=f'C4ClockBad{i}:\n lea error(pc),a0\n move.l #{1000+i},(a0)\n bra.w C1Fault\n'
asm+='C4ClockChecked: dc.l 0\nC4ClockSaved: ds.b 24\n'
import json
(r/'tools/tmp_final_clock_fixture.s').write_text(asm)
(r/'manifest/step5-c4-clock-cases.json').write_text(json.dumps(cases,indent=2)+'\n')

from pathlib import Path
import os,json
r=Path(__file__).resolve().parents[1]
os.environ['C1_ARCH']='000'
s=(r/'tools/build_step5_c1.py').read_text().replace('step5-c1','step5-c4-final-clock-test')
s=s.replace("'-m68'+arch,", "'-m68'+arch,'-DFF1_COARSE_NATIVE_000=1','-DFF1_NATIVE_000_STAGE=3','-DFF1_COARSE_200=1','-DFF1_COARSE_200_COMPLETE=1','-DFF1_PRODUCT_AB=1','-DFF1_DIV200_AB=1','-DFF1_NATIVEMUL200_AB=1','-DFF1_RESET200_AB=1','-DFF1_CROSS200_AB=1','-DFF1_ROOTLEAD_AB=1','-DFF1_SMALLROOT_AB=1','-DFF1_C4_BLIT_GUARD=1','-DFF1_C4_ROAD_PREFETCH=1','-DFF1_C4_ROOT_SEED=1','-DFF1_C4_MUL_INLINE=1','-DFF1_C4_DIV_LIMIT=1','-DFF1_C4_MUL_WORD=1','-DFF1_C4_HOOK_P5=1','-DFF1_C4_CONTEXT_P5=1','-DFF1_C4_BOUNDARY_P5=1',")
# Explicit binding of the audited native signature/site table.
s=s.replace("('native',2,1)]", "('native',2,1),('baseline',0,0),('baseline-render',0,1)]")
s=s.replace("(o/(variant+'.slave')).write_bytes", "struct.pack_into('>H',b,size+symbols['C4Enabled'],1)\n struct.pack_into('>H',b,size+symbols['C4ResponseSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4ReturnSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4NativeHeading'],1)\n struct.pack_into('>H',b,size+symbols['FF1ProductControl'],0)\n struct.pack_into('>H',b,size+symbols['FF1Div200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1NativeMul200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1Reset200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1Cross200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1RootLeadControl'],0)\n struct.pack_into('>H',b,size+symbols['C4ProjectionSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['FF1SmallRootControl'],0)\n struct.pack_into('>H',b,size+symbols['C4BlitEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4RoadPrefetchEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4RootSeedControl'],0)\n struct.pack_into('>H',b,size+symbols['FF1MulInlineControl'],0)\n struct.pack_into('>H',b,size+symbols['FF1DivLimitControl'],0)\n b[size+symbols['FF1NativeMulP4Gate']:size+symbols['FF1NativeMulP4Gate']+4]=bytes.fromhex('4e714e71')\n struct.pack_into('>H',b,size+symbols['C3Enabled'],3)\n if True:\n  for name in ['velocity_671e6','bridge_6720e','bridge_68546','velocity_68576','velocity_6721c','velocity_685a6']:\n   off=size+symbols['C4P5Gate_'+name];b[off:off+4]=bytes.fromhex('4e714e71')\n  struct.pack_into('>H',b,size+symbols['C4P5RotateSave']+2,0xf8c0)\n  struct.pack_into('>H',b,size+symbols['C4P5RotateRestore']+2,0x031f)\n if False:\n  for name in ['C4P5VelocityGate','C4P5PositionGate']:\n   off=size+symbols[name];b[off:off+8]=bytes.fromhex('c0fc000c4e714e71')\n struct.pack_into('>H',b,size+symbols['C4BoundaryControl'],1 if variant.startswith('baseline') else 0)\n (o/(variant+'.slave')).write_bytes")
extra="data_candidates=[]\nfragment(symbols['FF1Track000Signature'],0x6977a,0x112,'lookahead signature')\nfragment(symbols['FF1Track000Signature']+0x112,0x67514,0x16,'lookahead caller signature')\nfragment(symbols['FF1Trig000Signature'],0x24fe0,64,'trig signature')\n"
t=(r/'tools/build_step5_b7_bindings.py').read_text()
displaced=t[t.index('# UpdateHooks deliberately'):t.index('# NativeExact')].replace("symbols['schedule_install']","symbols['FF1MultiplyU64_000']")
extra=displaced+extra
s=s.replace(repr('data_candidates=[]\n').replace("'", '"'),repr(extra))
s=s.replace('lea C1RecordBuffer(pc),a1',r'lea C1Record(pc),a1\n adda.w #((C1RecordBuffer-C1Record)/2),a1\n adda.w #((C1RecordBuffer-C1Record)-(C1RecordBuffer-C1Record)/2),a1')
s=s.replace("(o/'fine.s').write_text(s)","s+='\\n include \"FerrariFormulaOne_Coarse200RootTable.s\"\\n include \"FerrariFormulaOne_Coarse200BoundaryTable.s\"\\n'\n(o/'fine.s').write_text(s)")
s=s.replace('base=(r/', "import shutil\nshutil.copy(r/'tools/tmp_final_clock_fixture.s',o/'clock-tests.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' lea public_bindings(pc),a1',' lea public_table(pc),a1\\n adda.l #(public_bindings-public_table),a1').replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w C4TestClocks'))\nbase=(r/",1)
s=s.replace('public_bindings:', ' include "clock-tests.s"\\npublic_bindings:')
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))

# The two assembly passes must retain every binding's operand offset and value.
import struct
for entry in json.loads((o/'bindings.json').read_text()):
 assert struct.unpack_from('>H',(o/'fine.bin').read_bytes(),entry['offset'])[0]==entry['expected'],entry
