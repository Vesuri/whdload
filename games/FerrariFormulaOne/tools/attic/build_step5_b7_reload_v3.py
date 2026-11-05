from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_b7_v3.py').read_text()
s=s.replace("'tmp/build/step5-b7-v3'+", "'tmp/build/step5-b7-v3-reload'+")
at=s.index("if os.environ.get('B7_TRANSITION'):")
patch='''
s=s.replace('FF1PresentationAfterTick:\\n rts', """FF1PresentationAfterTick:
 cmpi.l #10,schedule_completed(pc)
 bne.w .done
 tst.l public_reload_count(pc)
 bne.w .done
 movem.l d0-d7/a0-a6,-(sp)
 lea (public_reload_count.l,pc),a0
 move.l #1,(a0)
 move.l public_table(pc),a0
 move.l 160*4(a0),d0
 lsl.l #2,d0
 lea (public_reload_old.l,pc),a1
 move.l d0,(a1)
 move.l d0,a1
 move.l -4(a1),d0
 lea (public_reload_size.l,pc),a1
 move.l d0,(a1)
 move.l (a0),d0
 lsl.l #2,d0
 addi.l #4+$35c,d0
 move.l d0,a0
 move.l public_descriptor(pc),a4
 jsr (a0)                     ; real hooked native unloader, before FreeMem
 move.l public_reload_size(pc),d0
 lea (public_reload_hold.l,pc),a0
 bsr.l FF1PublicAcquire        ; occupy the freed primary block for relocation
 move.l public_table(pc),a0
 move.l (a0),d0
 lsl.l #2,d0
 addq.l #4,d0
 move.l d0,a0
 move.l 12(a0),a1
 move.l public_descriptor(pc),d0
 sub.l a1,d0
 lsr.l #2,d0
 sub.l (a1),d0
 adda.l #$244,a0
 jsr (a0)                     ; native overlay loader enters a fresh race
 ; Fixture stops in the new race before returning into old native frames.
.stopped: bra.b .stopped
.done:
 rts""")
s=s.replace(' move.l a4,a2\\n move.l $18(a3),d0', ' lea (public_descriptor.l,pc),a0\\n move.l a3,(a0)\\n move.l a4,a2\\n move.l $18(a3),d0')
s=s.replace(' move.l 160*4(a2),(a0)\\n lea start(pc),a2', ' move.l 160*4(a2),(a0)\\n lea (public_reload_hold.l,pc),a0\\n bsr.l FF1PublicRelease\\n lea start(pc),a2')
s=s.replace('public_control: dc.w 0', 'public_reload_count: dc.l 0\\npublic_descriptor: dc.l 0\\npublic_reload_old: dc.l 0\\npublic_reload_size: dc.l 0\\npublic_reload_hold: ds.l 2\\npublic_control: dc.w 0')
'''
s=s[:at]+patch+s[at:]
p=r/'tools/build_step5_b7_reload_generated.py';p.write_text(s)
exec(compile(s,str(p),'exec'))
