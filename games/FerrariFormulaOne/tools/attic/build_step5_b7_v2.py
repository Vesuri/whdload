from pathlib import Path
import subprocess,struct,re,os
r=Path(__file__).resolve().parents[1];variant=os.environ.get('B7_VARIANT','lean');o=r/('tmp/build/step5-b7-v2'+('-transition' if os.environ.get('B7_TRANSITION') else '-control' if os.environ.get('B7_CONTROL') else '-failure' if os.environ.get('B7_FAIL') else ''))/variant;o.mkdir(parents=True,exist_ok=True);base=(r/'tmp/build/step5-b7-loader-v2/FerrariFormulaOne.slave').read_bytes();size=len(base[32:-4]);assert size<32768
s=(r/f'tmp/build/step5-b6-s5/{variant}/fine.s').read_text().replace('#5440',f'#{size}').replace('#5388',f'#{size-52}')
s=s.replace('start:\n add.l $1c(a3),d0\n', 'start:\n move.l d0,-(sp)\n move.l selection_path(pc),d0\n cmpi.l #2,d0\n movem.l (sp)+,d0\n beq.b .fine\n rts\n.fine:\n bsr.l public_bind\n',1).replace(' cmp.l #$64a68,d0',' cmpi.l #2,selection_path(pc)\n bne.w done\n cmp.l #$64a68,d0',1)
s=s.replace(' move.w #$0002,$24fd0.l\n move.w #$4f76,$24fd2.l',' move.l #$24f76,$24fd0.l').replace(' move.w #$0002,$24fd4.l\n move.w #$4fa8,$24fd6.l',' move.l #$24fa8,$24fd4.l')
host_listing=(r/'tmp/build/step5-b7-loader-v2/build.list').read_text(errors='replace')
stack_owner=int(re.search(r'^FF1PublicStackOwner\s+00:([0-9A-F]+)',host_listing,re.M)[1],16)
s=s.replace(' bsr.l public_bind\n',' bsr.l public_bind\n cmpi.l #2,selection_path(pc)\n bne.b public_early_done\n bsr.l public_install_lifetime\n bsr.l public_begin_early\npublic_early_done:\n',1)
s=s.replace('done:\n move.w (sp)+,ccr','done:\n bsr.l public_seal\n move.w (sp)+,ccr',1)
s=s.replace(' cmpi.l #126,(a0)\n bne.w finish',' cmpi.l #126,(a0)\n bne.w finish\n bsr.l public_begin\n cmpi.l #2,selection_path(pc)\n bne.w finish',1)
s=s.replace('finish:\n bsr.w schedule_begin',' bsr.l public_seal\nfinish:\n bsr.w schedule_begin',1)
s=s.replace(' bsr.l public_begin\n cmpi.l #2,selection_path(pc)\n bne.w finish',' bsr.l public_begin\n cmpi.l #2,selection_path(pc)\n bne.w finish\n bsr.l public_install_boundary\n cmpi.l #2,selection_path(pc)\n bne.w finish',1)
s+='\n include \"FerrariFormulaOne_PublicLifecycle.s\"\npublic_reset_ranges:\n incbin \"reset.bin\"\n'
s+='''
public_return: rts
public_bind:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$22f30,(a3)
 bne.w .done
 cmpi.l #2,selection_path(pc)
 bne.w .done
 move.l a4,a2
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a2
 lea (public_table.l,pc),a0
 move.l a2,(a0)
 move.l 160*4(a2),d0
 cmp.l public_bound(pc),d0
 beq.w .done
 ; Qualify every CPU hunk. Slot 46 contains the original Chip-only audio data.
 moveq #0,d5
.qualify:
 cmpi.w #46*4,d5
 beq.b .next
 move.l 0(a2,d5.w),d2
 lsl.l #2,d2
 subq.l #4,d2
 move.l d2,a0
 move.l (a0),d3
 moveq #1,d0
 moveq #2,d1
 bsr.l FF1SelectProfile
 cmpi.l #2,d0
 bne.b .coarse
.next:
 addq.w #4,d5
 cmpi.w #206*4,d5
 blo.b .qualify
 lea start(pc),a0
 lea (public_bindings.l,pc),a1
 bsr.l FF1ApplyBindings
 tst.l d0
 bne.b .bad
 lea (public_bound.l,pc),a0
 move.l 160*4(a2),(a0)
 lea start(pc),a2
 suba.l #HOSTSIZE,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 bra.b .done
.coarse:
 lea (selection_path.l,pc),a0
 move.l #1,(a0)
 move.l #100,4(a0)
 bra.b .done
.bad:
 lea (public_binding_error.l,pc),a0
 move.l d0,(a0)
 bra.b .coarse
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
public_control: dc.w 0
public_table: dc.l 0
public_bound: dc.l 0
public_binding_error: dc.l 0
public_marker: dc.b 'FF1B7BOUNDHOOK',0
 even
 include "FerrariFormulaOne_Bindings.s"
 include "FerrariFormulaOne_PublicMemory.s"
public_bindings:
 incbin "bindings.bin"
'''.replace('HOSTSIZE',str(size))
s=s.replace(' ; Qualify every CPU hunk.', ' lea start(pc),a0\n suba.l #HOSTSIZE,a0\n move.l STACKOWNER(a0),d2\n move.l STACKOWNER+4(a0),d3\n moveq #1,d0\n moveq #2,d1\n bsr.l FF1SelectProfile\n cmpi.l #2,d0\n bne.w .coarse\n ; Qualify every CPU hunk.'.replace('HOSTSIZE',str(size)).replace('STACKOWNER',str(stack_owner)))
if os.environ.get('B7_TRANSITION'):
 s=s.replace('FF1PresentationAfterTick:\n rts', """FF1PresentationAfterTick:
 movem.l d0/a0,-(sp)
 move.w ccr,-(sp)
 cmpi.l #10,schedule_completed(pc)
 bne.b .done
 cmpi.l #2,public_exits(pc)
 bhs.b .done
 move.w #1,$66be0
 lea (public_exits.l,pc),a0
 addq.l #1,(a0)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0
 rts""")
 s=s.replace('public_table: dc.l 0','public_exits: dc.l 0\npublic_table: dc.l 0')
if os.environ.get('B7_CONTROL'):s=s.replace('public_control: dc.w 0','public_control: dc.w 1')
(o/'reset.bin').write_bytes(struct.pack('>I',0xffffffff))
(o/'fine.s').write_text(s);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-b6-s5/lean/original_div.bin').read_bytes());(o/'bindings.bin').write_bytes(struct.pack('>I',0xffffffff))
args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1','-DFF1_HELPERS_020=1','-DFF1_NATIVE_EXACT=5','-DFF1_PUBLIC_BINDINGS=1','-DFF1_PUBLIC_PATCHES=1','-DFF1_PUBLIC_LIFECYCLE=1','-DFF1_PUBLIC_MEMORY=1',f'-DFF1_HOST_CODE_SIZE={size}','-L','fine.list','-o','fine.bin']
if os.environ.get('B7_FAIL'):args+=['-DFF1_PATCH_LEDGER_BYTES=0']
if variant=='verify':args+=['-DVERIFY=1','-DFF1_SPEED_RECORD_CAPACITY=256']
subprocess.run(args+['fine.s'],cwd=o,check=True)
subprocess.run([os.sys.executable,str(r/'tools/build_step5_b7_bindings.py'),str(o)],check=True)
subprocess.run([os.sys.executable,str(r/'tools/build_step5_b7_reset.py'),str(o)],check=True)
subprocess.run(args+['fine.s'],cwd=o,check=True)
normal=bytearray(base[32:-4]);listing=(o/'fine.list').read_text();entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+entry<32768
struct.pack_into('>H',normal,24,size+entry);pos=normal.find(bytes.fromhex('4e714e714e716000'));assert pos>=0;normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/'fine.bin').read_bytes();normal+=b'\0'*((-len(normal))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(normal)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+normal+bytes.fromhex('000003f2'));print('B7',variant,'size',len(normal),'host',size)
