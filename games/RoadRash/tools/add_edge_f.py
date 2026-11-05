from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text();s=s.replace(' bsr f_dda_init',' bsr f_edge_init\n bsr f_dda_init',1)
s+='''
f_edge_init:
 lea f_main(pc),a0
 move.l a5,(a0)
 move.l a5,a1
 adda.l #$310e2,a1
 lea f_road_colors(pc),a0
 move.w #$4eb9,(a1)
 move.l a0,2(a1)
 move.l a5,a1
 adda.l #$31994,a1
 lea f_edge(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 rts
f_main: dc.l 0
f_edge_choices: ds.l 4
f_road_colors:
 move.l f_main(pc),a5
 move.l $31960(a5),a5
 movem.l d0-d3/a0-a2,-(a7)
 lea f_edge_choices(pc),a0
 moveq #0,d3
.state:
 moveq #0,d0
 moveq #0,d1
 move.w d3,d1
 andi.w #1,d1
 lsl.w #3,d1
 lea $20(a5,d1.w),a1
 moveq #3,d2
.outer:
 tst.w (a1)+
 sne d1
 add.b d1,d1
 addx.w d0,d0
 dbf d2,.outer
 move.w d3,d1
 andi.w #2,d1
 lsl.w #2,d1
 lea $10(a5,d1.w),a1
 moveq #3,d2
.inner:
 tst.w (a1)+
 sne d1
 add.b d1,d1
 addx.w d0,d0
 dbf d2,.inner
 add.w d0,d0
 lea f_edge_offsets(pc),a1
 move.w (a1,d0.w),d1
 lea f_edge_code(pc),a1
 adda.w d1,a1
 move.l a1,(a0)+
 addq.w #1,d3
 cmpi.w #4,d3
 bne .state
 movem.l (a7)+,d0-d3/a0-a2
 rts
f_edge:
 movem.l d1/d3/a0,-(a7)
 move.l d4,d1
 move.l d6,d3
 moveq #0,d4
 moveq #0,d6
 move.l f_main(pc),a0
 move.l $31950(a0),a0
 move.w -4(a0),d0
 swap d0
 move.w -4(a0),d0
 and.l d1,d0
 move.w -2(a0),d2
 swap d2
 move.w -2(a0),d2
 and.l d1,d2
 move.w d7,d1
 lsr.w #8,d1
 lsr.w #3,d1
 andi.w #12,d1
 lea f_edge_choices(pc),a0
 move.l (a0,d1.w),a0
 jmp (a0)
f_edge_return:
 movem.l (a7)+,d1/d3/a0
 rts
f_edge_offsets:
'''
for n in range(256):s+=f' dc.w f_edge_{n}-f_edge_code\n'
s+='f_edge_code:\n'
for n in range(256):
 s+=f'f_edge_{n}:\n'
 for bit,reg in zip([7,6,5,4],['d0','d2','d4','d6']):
  if n&(1<<bit):s+=f' or.l d5,{reg}\n'
 for bit,reg in zip([3,2,1,0],['d0','d2','d4','d6']):
  if n&(1<<bit):s+=f' or.l d3,{reg}\n'
 s+=' bra.w f_edge_return\n'
p.write_text(s)
