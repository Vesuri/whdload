from pathlib import Path
src=Path('src');out=Path('tmp/build').resolve()
p=(src/'timing-runtime-present.i').read_text()
p=p.replace(' movea.l RT_DRAW_ENTRY(a0),a1',' move.l a0,-(sp)\n bsr frame_probe_begin\n movea.l RT_DRAW_ENTRY(a0),a1')
p=p.replace(' jsr (a1)\n moveq #0,d0',' jsr (a1)\n movea.l (sp)+,a0\n bsr frame_probe_end\n moveq #0,d0')
p+='''
frame_probe_begin:
 movem.l d0-d2/a0-a3,-(sp)
.base:
 lea .base(pc),a1
 adda.l #frame_probe_data-.base,a1
 move.l 8(a1),d0
 andi.l #511,d0
 mulu.w #48,d0
 lea 16(a1),a2
 adda.l d0,a2
 move.l a2,12(a1)
 move.l RT_CLOCK+TC_LAST(a0),(a2)+
 move.l RT_SCHEDULER+TS_WORLDS(a0),(a2)+
 movea.l RT_HUNKS+8(a0),a3
 move.l $1c(a3),(a2)+
 clr.l (a2)+
 lea RT_CAMERA(a0),a3
 moveq #5,d0
.camera:
 move.w (a3)+,(a2)+
 dbf d0,.camera
 lea RT_PACKET(a0),a3
 moveq #4,d0
.packet:
 move.w (a3)+,(a2)+
 dbf d0,.packet
 movea.l RT_HUNKS+24(a0),a3
 move.l $3b88(a3),(a2)+
 move.w $3ba4(a3),(a2)+
 move.l RT_RECORD+TR_COMMAND(a0),(a2)+
 movem.l (sp)+,d0-d2/a0-a3
 rts
frame_probe_end:
 movem.l d0/a0-a2,-(sp)
.base:
 lea .base(pc),a1
 adda.l #frame_probe_data-.base,a1
 movea.l 12(a1),a2
 movea.l RT_HUNKS+8(a0),a0
 move.l $1c(a0),12(a2)
 addq.l #1,8(a1)
 movem.l (sp)+,d0/a0-a2
 rts
'''
p,helpers=p.split('\nframe_probe_begin:',1)
(out/'frame-present.i').write_text(p)
(out/'frame-helpers.i').write_text('frame_probe_begin:'+helpers)
c=(src/'timing-core.i').read_text().replace('"timing-runtime-present.i"',f'"{out}/frame-present.i"');c+=f'\n include "{out}/frame-helpers.i"\n';(out/'frame-core.i').write_text(c)
s=(src/'GunshipHD.s').read_text().replace('"timing-core.i"',f'"{out}/frame-core.i"');s=s.rsplit('\tEND',1)[0]+'''\n even
frame_probe_data:
 dc.b "GSFRAME1"
 dc.l 0,0
 ds.b 512*48
 END
''';(out/'frame-probe.s').write_text(s)
