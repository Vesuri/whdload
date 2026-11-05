"""Build an isolated coarse native-step candidate on the existing public loader."""
from pathlib import Path
import os,struct,re,subprocess
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
arch=os.environ.get('C1_ARCH','000');verify=os.environ.get('C1_VERIFY')=='1';o=r/('tmp/build/step5-c1'+('-verify' if verify else ''))/arch;o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes();size=len(base[32:-4])
s='''start:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$22f30,(a3)
 bne.w done
 move.l selection_path(pc),d0
 cmpi.l #1,d0
 bne.w done
 move.l a4,a2
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a2
 lea public_table(pc),a0
 move.l a2,(a0)
 move.l 160*4(a2),d0
 cmp.l public_bound(pc),d0
 beq.w done
 lea start(pc),a0
 lea public_bindings(pc),a1
 bsr.w FF1ApplyBindings
 tst.l d0
 bne.w C1Fault
 lea public_bound(pc),a0
 move.l 160*4(a2),(a0)
 bsr.w C1InstallUnload
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Ledger(pc),a0
 move.l public_table(pc),a1
 bsr.w FF1PatchBegin
 tst.l d0
 bne.w C1Fault
 move.w #$4ef9,$65174
 lea C1Head(pc),a0
 move.l a0,$65176
 move.w #$4eb9,$6a304
 lea s2_rng_control(pc),a0
 move.l a0,$6a306
 ; All race exits funnel through the original cleanup call at $65f48.
 lea C1Exit(pc),a0
 move.w #$4ef9,$65f48
 move.l a0,$65f4a
 lea C1Ledger(pc),a0
 bsr.w FF1PatchSeal
 tst.l d0
 bne.w C1Fault
 bsr.w C1Flush
 move.l $4.w,a6
 jsr -126(a6)
done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
C1Flush:
 movem.l d0-d7/a0-a6,-(sp)
 lea start(pc),a2
 suba.l #HOSTSIZE,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''.replace('HOSTSIZE',str(size))
old=(r/'tmp/build/step5-b8-v3/lean/fine.s').read_text()
boot=old[old.index('selection_boot:'):old.index(' include "FerrariFormulaOne_UpdateHooks.s"')]
boot=boot.replace('#6384',f'#{size}').replace('#6332',f'#{size-52}')
s+=boot
rng=old[old.index('s2_rng_control:'):old.index('FF1PresentationAfterTick:')]
if arch=='000':rng=rng.replace('move.w ccr,-(sp)','move.w sr,-(sp)')
s+=rng
s+='\n include "FerrariFormulaOne_Coarse.s"\n'
s+='''
C1Activate:
 movem.l d0-d7/a0-a6,-(sp)
 move.w C1Control(pc),d0
 cmpi.w #2,d0
 bne.b .split
 lea C1NativeEnd(pc),a0
 move.w #$4ef9,$65f2e
 move.l a0,$65f30
 bsr.w C1Flush
 movem.l (sp)+,d0-d7/a0-a6
 rts
.split:
 ; Host ledger owns every changed native word until native race exit/unload.
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Ledger(pc),a0
 move.l public_table(pc),a1
 bsr.w FF1PatchBegin
 tst.l d0
 bne.w C1Fault
 bsr.w FF1InstallPresentation
 move.l error(pc),d0
 bne.w C1Fault
'''
# Explicit patch sites are checked against the unmodified native image before
# any site is changed. Signature operands are bound by native relocation identity.
patches=[(0x654ec,'C1SkipSwap',6),(0x65606,'FF1SimulationTail',6),(0x65f2e,'C1End',6),(0x24946,'C1Vbl',6),(0x65dca,'FF1ClockTick',6),(0x65dd8,'FF1ClockTick',6),(0x6c20c,'C1RecoveryEntry',6),(0x6c5de,'C1RecoveryClear',6),(0x6c5f6,'C1RecoveryBody',6),(0x6c6ea,'C1RecoveryDraw',6),(0x6c7c8,'C1RecoveryExit',6),(0x653fc,'C1Pause',6),(0x654b8,'C1Resume',6)]
native=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
checks=''
for addr,label,n in patches:
 for i in range(0,n,2):checks+=f' cmpi.w #${int.from_bytes(native[addr+i:addr+i+2],"big"):04x},${addr+i:x}\n bne.w C1Fault\n'
# Must check before the shared installer mutates anything too.
s=s.replace(' bsr.w FF1InstallPresentation',checks+' bsr.w FF1InstallPresentation',1)
for addr,label,n in patches:
 op=0x4eb9 if addr in (0x24946,0x65dca,0x65dd8,0x653fc,0x654b8) else 0x4ef9
 s+=f' lea {label}(pc),a0\n move.l a0,${addr+2:x}\n move.w #${op:x},${addr:x}\n'
s+=''' lea C1Context(pc),a0
 moveq #100,d0
 bsr.w FF1TimeInit
 lea C1Active(pc),a0
 move.w #1,(a0)
 lea C1Ledger(pc),a0
 bsr.w FF1PatchSeal
 tst.l d0
 bne.w C1Fault
 bsr.w C1Flush
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
C1SkipSwap:
 ; Preserve native per-step buffer views independently of physical publication.
 move.l $226ae,d0
 move.l $226b2,$226ae
 move.l d0,$226b2
 jmp $65542
C1InstallUnload:
 move.l C1UnloadInstalled(pc),d0
 bne.b .done
 move.l public_table(pc),a0
 move.l (a0),d0
 lsl.l #2,d0
 addi.l #4+$35c,d0
 move.l d0,a0
 cmpi.l #$48e7e00e,(a0)
 bne.w C1Fault
 cmpi.l #$202c0004,4(a0)
 bne.w C1Fault
 move.w #$4ef9,(a0)
 lea C1Unload(pc),a1
 move.l a1,2(a0)
 move.w #$4e71,6(a0)
 addq.l #8,d0
 lea C1UnloadJump+2(pc),a1
 move.l d0,(a1)
 lea C1UnloadInstalled(pc),a0
 move.l #1,(a0)
.done:
 rts
C1UnloadInstalled: dc.l 0
C1Ledger: ds.b 24
public_table: dc.l 0
public_bound: dc.l 0
 include "FerrariFormulaOne_PublicPatches.s"
 include "FerrariFormulaOne_PublicMemory.s"
 include "FerrariFormulaOne_Bindings.s"
public_bindings:
 incbin "bindings.bin"
'''
a=s.index('selection_boot:');z=s.index('C1Activate:');end=s.index('public_table: dc.l 0',z)
s=' include \"FerrariFormulaOne_CoarseInstall.s\"\n'+s[a:z]+s[end:]
if verify:
 import json
 blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2),dict(name='pit_flags',address='0xd0dc',bytes=8)]
 record='C1Record:\n lea C1RecordBuffer(pc),a1\n'
 for block in blocks:
  record+=f" lea ${int(block['address'],16):x},a0\n move.w #{block['bytes']//2-1},d0\n.{block['name']}:\n move.w (a0)+,(a1)+\n dbra d0,.{block['name']}\n"
 record+=' rts\n'
 s=s.replace('public_table: dc.l 0',record+'public_table: dc.l 0')
 s+='C1RecordBuffer: ds.b '+str(sum(x['bytes'] for x in blocks))+'\n'
 (o/'blocks.json').write_text(json.dumps(blocks,indent=2))
(o/'fine.s').write_text(s);(o/'bindings.bin').write_bytes(struct.pack('>I',0xffffffff))
args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68'+arch,'-Fbin','-quiet','-I'+str(repo/'Games'),f'-DFF1_HOST_CODE_SIZE={size}','-DFF1_COARSE_STEP=1','-DFF1_RENDER_POSES=1','-DFF1_PUBLIC_BINDINGS=1','-DFF1_PUBLIC_PATCHES=1','-DFF1_PUBLIC_MEMORY=1','-L','fine.list','-o','fine.bin','fine.s']
if verify:args.insert(1,'-DFF1_COARSE_VERIFY=1')
if arch=='020':args.insert(1,'-DFF1_COARSE_020=1')
subprocess.run(args,cwd=o,check=True)
# Use the existing instruction/relocation binding engine; omit fine-only tables.
t=(r/'tools/build_step5_b7_bindings.py').read_text()
a=t.index('# UpdateHooks deliberately');z=t.index('(b/\'bindings.json\')',a)
t=t[:a]+"data_candidates=[]\n"+t[z:]
t=t.replace("symbols['public_bind']","symbols.get('public_bind',len(code))")
(r/'tools/build_step5_c1_bindings.py').write_text(t)
subprocess.run([os.sys.executable,str(r/'tools/build_step5_c1_bindings.py'),str(o)],check=True)
subprocess.run(args,cwd=o,check=True)
normal=bytearray(base[32:-4]);listing=(o/'fine.list').read_text();symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
struct.pack_into('>H',normal,24,size+symbols['selection_boot']);pos=normal.find(bytes.fromhex('4e714e714e716000'));assert pos>=0
normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/'fine.bin').read_bytes();normal+=b'\0'*((-len(normal))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(normal)//4);h[28:32]=h[20:24]
for variant,control,draw in [('candidate',0,1),('omitted',0,0),('control',1,0),('native',2,1)]:
 b=bytearray(normal)
 struct.pack_into('>H',b,size+symbols['C1Control'],control);struct.pack_into('>H',b,size+symbols['C1DrawEnabled'],draw)
 (o/(variant+'.slave')).write_bytes(h+b+bytes.fromhex('000003f2'))
print('C1',arch,'bytes',len(normal))
