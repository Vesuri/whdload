#!/usr/bin/env python3
"""Build a VERIFY-only, hash-guarded SPS/A500 diagnostic; release stays unchanged."""
from pathlib import Path
import struct,subprocess,os,json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'tmp/build/step2';out.mkdir(parents=True,exist_ok=True)
slow=int(os.environ.get('SLOW_FIELDS','0'));profile=int(os.environ.get('PROFILE_WINDOW','1'));warp=int(os.environ.get('WARP_OFF','0'))
assert 0<=slow<=20
assert warp == 0, "Guest warp switching is retired; use the verified emulator monitor"
assert hashlib.sha256((root/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()).hexdigest() == 'b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
code=bytearray((root/'tmp/build/release/FerrariFormulaOne.slave').read_bytes());normal=code[32:-4];pos=normal.find(bytes.fromhex('d0ab001c2240'));assert pos>=0
# There are two version handlers; use the SPS (second) one.
pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
asm=f'''VERIFY EQU 1
SLOW_FIELDS EQU {slow}
PROFILE_WINDOW EQU {profile}
WARP_OFF EQU {warp}
start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 lea installs(pc),a0
 cmp.l #$64a68,d0
 bne.w done
 tst.l (a0)
 bne.w done
 cmpi.l #$4eb90006,$65600
 bne.w bad
 cmpi.w #$7120,$65604
 bne.w bad
 cmpi.l #$4eb90002,$654e6
 bne.w bad
 cmpi.w #$a130,$654ea
 bne.w bad
 addq.l #1,(a0)
 lea simulation(pc),a0
 move.l a0,$65602
 lea completed(pc),a0
 move.l a0,$654e8
 lea publication(pc),a0
 move.l a0,$654f8
 lea geometry(pc),a0
 move.l a0,$6b36e
 lea mouse(pc),a0
 move.w #$4eb9,$24824
 move.l a0,$24826
 bra.w done
bad:
 lea error(pc),a0
 move.l #1,(a0)
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
simulation:
 jsr $67120
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 lea updates(pc),a0
 addq.l #1,(a0)
 lea sim_sp(pc),a0
 move.l sp,(a0)
simulation_done:
 nop
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
geometry:
 movem.l d0/a0,-(sp)
 move.w sr,-(sp)
 lea geometry_calls(pc),a0
 addq.l #1,(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0
 jmp $6a2d0
completed:
 jsr $2a130
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 lea renders(pc),a0
 addq.l #1,(a0)
 IFD VERIFY
 IFNE SLOW_FIELDS
 moveq #SLOW_FIELDS-1,d7
 move.l $4.w,a6
 move.l $9c(a6),a6
slow_loop:
 jsr -270(a6)
 dbra d7,slow_loop
 ENDC
 ENDC
 IFNE WARP_OFF
 lea warp_sent(pc),a0
 tst.l (a0)
 bne.b after_warp
 move.l updates(pc),d0
 cmpi.l #110,d0
 blo.b after_warp
 move.l #1,(a0)
 clr.l -(sp)
 clr.l -(sp)
 clr.l -(sp)
 pea warp_command(pc)
 move.l #-1,-(sp)
 move.l #82,-(sp)
 jsr $f0ff60
 lea 24(sp),sp
 lea warp_result(pc),a0
 move.l d0,(a0)
after_warp:
 ENDC
render_done:
 nop
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
publication:
 ; Original argument must remain at 4(sp): tail call preserves C ABI.
 movem.l d0/a0,-(sp)
 move.w sr,-(sp)
 lea publications(pc),a0
 addq.l #1,(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0
 jmp $2428a
mouse:
 movem.l d1-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 lea fields(pc),a0
 addq.l #1,(a0)
 lea irq_sp(pc),a0
 move.l sp,(a0)
 IFNE PROFILE_WINDOW
 lea profile_once(pc),a0
 tst.l (a0)
 bne.b mouse_end
 move.l updates(pc),d0
 cmpi.l #120,d0
 blo.b mouse_end
 move.l #1,(a0)
 bsr profile_prepare
profile_ready:
 nop
 bsr profile_restore
profile_restored:
 nop
 ENDC
mouse_end:
 move.w (sp)+,ccr
 movem.l (sp)+,d1-d7/a0-a6
 move.w $dff00a,d0
 rts
profile_prepare:
 movem.l d0-a6,-(sp)
 lea profile_state(pc),a6
 move.w sr,(a6)
 ori.w #$0700,sr
 move.l $4.w,a0
 move.l 276(a0),a0
 cmpi.b #13,8(a0)
 bne.b profile_bad
 move.l a0,2(a6)
 move.l 128(a0),6(a6)
 move.l 140(a0),10(a6)
 lea $1000.w,a1
 lea 14(a6),a2
 moveq #7,d0
save_scratch:
 move.l (a1)+,(a2)+
 dbra d0,save_scratch
 move.l #1,$1000.w
 clr.l $1004.w
 clr.l $1008.w
 move.l #$405,$100c.w
 move.l #$80000003,$1010.w
 clr.l $1014.w
 move.l #$400,128(a0)
 clr.l 140(a0)
 movem.l (sp)+,d0-a6
 rts
profile_bad:
 lea error(pc),a0
 move.l #2,(a0)
 movem.l (sp)+,d0-a6
 rts
profile_restore:
 movem.l d0-a6,-(sp)
 lea profile_state(pc),a6
 move.l 2(a6),a0
 move.l 6(a6),128(a0)
 move.l 10(a6),140(a0)
 lea $1000.w,a1
 lea 14(a6),a2
 moveq #7,d0
restore_scratch:
 move.l (a2)+,(a1)+
 dbra d0,restore_scratch
 movem.l (sp)+,d0-a6
 move.w profile_state(pc),sr
 rts
warp_command: dc.b "SPC_WARP 0",0
 even
installs: dc.l 0
error: dc.l 0
updates: dc.l 0
renders: dc.l 0
publications: dc.l 0
geometry_calls: dc.l 0
fields: dc.l 0
sim_sp: dc.l 0
irq_sp: dc.l 0
warp_sent: dc.l 0
warp_result: dc.l -1
profile_once: dc.l 0
profile_state: ds.b 46
'''
name=f'probe-s{slow}-p{profile}-w{warp}'
(out/f'{name}.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',str(out/f'{name}.list'),'-o',str(out/f'{name}.bin'),str(out/f'{name}.s')],check=True)
stub=(out/f'{name}.bin').read_bytes();size=len(normal)
normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71')
normal+=stub;normal+=b'\0'*((-len(normal))%4)
code[20:24]=struct.pack('>I',len(normal)//4);code[28:32]=code[20:24]
(out/f'{name}.slave').write_bytes(code[:32]+normal+bytes.fromhex('000003f2'))
print(name,len(stub),hex(pos))
