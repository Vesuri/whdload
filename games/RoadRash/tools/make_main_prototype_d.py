from pathlib import Path
import shutil
src=Path('src');dst=Path('tmp/d-main-prototype-source');shutil.copytree(src,dst)
p=dst/'RoadRashHD.s';s=p.read_text().replace('dc.l -$5000 ; optional WHDLoad-managed stack and guards','dc.l -$50000 ; private whole-image relocation feasibility allocation')
s=s.replace('.no_c:\n\tENDC','.no_c:\n\tbsr d_main_init\n\tENDC',1)
helper='''; PRIVATE feasibility probe: no production acceptance or toggle contract.
d_main_init:
 movem.l d0-d7/a0-a6,-(a7)
 move.l _expmem(pc),a5
 cmpa.l #$200000,a5
 bcs .done
 cmpa.l #$a00000,a5
 bcc .done
 cmpi.l #$3ec,$bc40c
 bne .done
 cmpi.l #5173,$bc410
 bne .done
 lea $5000(a5),a5
 lea $80000,a0
 move.l a5,a1
 move.w #$3c3ec/4-1,d0
.copy:
 move.l (a0)+,(a1)+
 dbf d0,.copy
 move.l a5,d7
 sub.l #$80000,d7
 lea $bc418,a3
 move.w #5173-1,d6
.fix:
 move.l (a3)+,d0
 move.l a5,a1
 adda.l d0,a1
 move.l (a1),d1
 cmpi.l #$80000,d1
 bcs .next
 cmpi.l #$bc3ec,d1
 bcc .next
 add.l d7,(a1)
.next:
 dbf d6,.fix
 lea expansion_memory(pc),a0
 move.l a5,(a0)
 move.w #$4ef9,$80000
 move.l a5,$80002
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
'''
s=s.replace('ReadSomeFile:\n',helper+'\nReadSomeFile:\n',1);p.write_text(s)
