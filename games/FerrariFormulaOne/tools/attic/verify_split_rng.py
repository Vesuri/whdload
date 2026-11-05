# Local fixture only. Establish the same race-entry randomness in both arms.
seed=(r/'tmp/step5/a1200-selection-entry-control-c20/entry.bin').read_bytes()
lines=['s2_rng_control:',' movem.l d0-a6,-(sp)',' move.w ccr,-(sp)',' lea s2_rng_done(pc),a0',' tst.w (a0)',' bne.w .done',' move.w #1,(a0)']
for lo,hi in ((0x24f60,0x24fd8),(0x1c8ac,0x1c8ae),(0x66f94,0x66f96)):
 for at in range(lo,hi,2):lines.append(f' move.w #${int.from_bytes(seed[at:at+2],"big"):04x},${at:x}.l')
lines+=['.done:',' move.w (sp)+,ccr',' movem.l (sp)+,d0-a6',' asl.w #1,d0',' ext.l d0',' move.l d0,a4',' rts','s2_rng_done: dc.w 0']
source=source.replace(' addq.l #1,(a0)\n lea (barrier.l,pc),a0',' move.w #$4eb9,$6a304\n lea s2_rng_control(pc),a1\n move.l a1,$6a306\n addq.l #1,(a0)\n lea (barrier.l,pc),a0',1)
source=source.replace(' IFND VERIFY\nvelocity_scratch equ velocity_records', '\n'.join(lines)+'\n IFND VERIFY\nvelocity_scratch equ velocity_records',1)
