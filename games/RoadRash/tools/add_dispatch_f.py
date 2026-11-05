from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace(' bsr f_edge_init',' bsr f_dispatch_init\n bsr f_edge_init',1)
s+='''
; F4: direct dispatch for the native nonnegative object-type namespace.
; Negative types retain their separate native overlay/split handling.
f_dispatch_init:
 lea f_dispatch_base(pc),a0
 move.l a5,d0
 addi.l #$30000,d0
 move.l d0,(a0)
 move.l a5,a1
 adda.l #$300fe,a1
 lea f_dispatch(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 rts
f_dispatch_base: dc.l 0
f_dispatch:
 cmpi.w #$234,d4
 bcc .done
 move.w d4,-(a7)
 add.w d4,d4
 lea f_dispatch_table(pc),a3
 move.w (a3,d4.w),d4
 move.l f_dispatch_base(pc),a3
 adda.w d4,a3
 move.w (a7)+,d4
 jmp (a3)
.done:
 rts
f_dispatch_table:
'''
ranges=[(0,0x59,0x32c),(0x5f,0x7e,0x1ae),(0x7f,0x87,0x190),(0x87,0x88,0x1de),(0x88,0xd8,0x1ee),(0x12c,0x13c,0x3f2),(0x154,0x159,0x10c),(0x159,0x15e,0x128),(0x15e,0x166,0x172),(0x166,0x16a,0x2cc),(0x16a,0x16e,0x300),(0x172,0x173,0x2ae),(0x173,0x186,0x520),(0x186,0x234,0x538)]
for n in range(0x234):
 t=next((t for lo,hi,t in ranges if lo<=n<hi),0x510)
 s+=f' dc.w ${t:04x} ; ${n:03x}\n'
p.write_text(s)
