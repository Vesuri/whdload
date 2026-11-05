from pathlib import Path
src=Path('src');out=Path('tmp/build').resolve()
p=(src/'timing-endpoint-player.i').read_text();assert p.count('\tbsr player_step_interval')==2
p=p.replace('\tbsr player_step_interval','\tbsr preview_key_probe\n\tbsr player_step_interval')
p+='''
; Diagnostic only: compare full preview inputs but never skip execution.
PK_KEY_SIZE equ MP_RECORD_SIZE+PS_SIZE+PS_INPUT_SIZE+12
preview_key_probe:
 movem.l d0-d7/a0-a6,-(sp)
 moveq #0,d0
 roxl.b #1,d0
 move.l d0,-(sp)
 lea 4(sp),a6
 suba.w #PK_KEY_SIZE,sp
 movea.l sp,a5
 moveq #MP_RECORD_SIZE/2-1,d1
.player:
 move.w (a1)+,(a5)+
 dbf d1,.player
 moveq #PS_SIZE/2-1,d1
.state:
 move.w (a0)+,(a5)+
 dbf d1,.state
 moveq #PS_INPUT_SIZE/2-1,d1
.packet:
 move.w (a4)+,(a5)+
 dbf d1,.packet
 move.l (a6),(a5)+
 move.l 40(a6),(a5)+
 move.l 44(a6),(a5)+
 lea preview_key_probe_data(pc),a4
 addq.l #1,8(a4)
 movea.l sp,a0
 lea preview_key_probe_previous(pc),a1
 lea preview_key_probe_changes(pc),a2
 moveq #0,d0
 move.w #PK_KEY_SIZE-1,d1
.compare:
 move.b (a0)+,d2
 cmp.b (a1),d2
 beq .equal
 moveq #1,d0
 addq.l #1,(a2)
.equal:
 move.b d2,(a1)+
 addq.l #4,a2
 dbf d1,.compare
 tst.w 16(a4)
 beq .first
 tst.w d0
 bne .done
 addq.l #1,12(a4)
.first:
 move.w #1,16(a4)
.done:
 adda.w #PK_KEY_SIZE,sp
 move.l (sp)+,d0
 lsr.b #1,d0
 movem.l (sp)+,d0-d7/a0-a6
 rts
preview_key_probe_data:
 dc.b "GSPKEY01"
 dc.l 0,0
 dc.w 0,PK_KEY_SIZE
preview_key_probe_changes: ds.l PK_KEY_SIZE
preview_key_probe_previous: ds.b PK_KEY_SIZE
 even
'''
(out/'preview-key-player.i').write_text(p)
c=(src/'timing-core.i').read_text().replace('"timing-endpoint-player.i"',f'"{out}/preview-key-player.i"');(out/'preview-key-core.i').write_text(c)
s=(src/'GunshipHD.s').read_text().replace('"timing-core.i"',f'"{out}/preview-key-core.i"');(out/'preview-key.s').write_text(s)
