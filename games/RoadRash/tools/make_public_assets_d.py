from pathlib import Path
import shutil
src=Path('src');dst=Path('tmp/d-public-assets-source');shutil.copytree(src,dst)
p=dst/'RoadRashHD.s';s=p.read_text().replace('dc.l -$50000 ; optional public main image, stack and reserved headroom','dc.l -$56000 ; optional main/bootstrap/stacks and 12 image-header slots').replace(' include public_boot.s',' include public_boot.s\n include public_assets.s',1).replace('ReadSomeFile:\n','ReadSomeFile:\n IFD C_PUBLIC_MAIN\n bsr public_asset_load_destination\n ENDC\n',1);p.write_text(s)
p=dst/'public_main.s';s=p.read_text().replace('.publish:\n','.publish:\n lea public_asset_pool(pc),a0\n move.l a5,d0\n addi.l #$4b000,d0\n move.l d0,(a0)\n move.l a5,a1\n adda.l #$2fd9c,a1\n lea public_asset_relocate(pc),a0\n move.w #$4ef9,(a1)\n move.l a0,2(a1)\n',1);p.write_text(s)
(dst/'public_assets.s').write_text('''; PRIVATE CPU-only SET headers: twelve typed low-memory image-set owners.
; Preserve native pixel pointers in Chip; translate a reload back to its
; original destination before native size/depack logic reads the owner again.
public_asset_relocate:
 ; Exact native $afd9c descriptor relocation, including its register results.
 move.w (a0),d7
 subq.w #1,d7
 bmi .native_done
 lea 2(a0),a2
.native:
 move.l (a2),d0
 add.l a0,d0
 move.l d0,(a2)
 lea 14(a2),a2
 dbf d7,.native
.native_done:
 move.w sr,-(a7)
 movem.l d0-d2/a0-a3,-(a7)
 move.l public_asset_pool(pc),a1
 cmpa.l #0,a1
 beq .done
 lea $432,a3
 moveq #11,d2
.owner:
 cmpa.l (a3),a0
 beq .copy
 addq.l #4,a3
 adda.l #2048,a1
 dbf d2,.owner
 bra .done
.copy:
 moveq #0,d0
 move.w (a0),d0
 beq .done
 mulu.w #14,d0
 addq.w #2,d0
 cmpi.w #2044,d0
 bhi .done
 move.l a0,(a1)+
 move.l a1,d1
 lsr.w #1,d0
 subq.w #1,d0
.words:
 move.w (a0)+,(a1)+
 dbf d0,.words
 move.l d1,(a3)
.done:
 movem.l (a7)+,d0-d2/a0-a3
 move.w (a7)+,ccr
 rts

public_asset_load_destination:
 movem.l d0-d1/a0/a2-a3,-(a7)
 move.l public_asset_pool(pc),a0
 cmpa.l #0,a0
 beq .done
 addq.l #4,a0
 lea $432,a3
 moveq #11,d0
.next:
 cmpa.l a0,a1
 beq .restore
 adda.l #2048,a0
 addq.l #4,a3
 dbf d0,.next
 bra .done
.restore:
 move.l -4(a0),a1
 move.l a1,(a3)
.done:
 movem.l (a7)+,d0-d1/a0/a2-a3
 rts
public_asset_pool:
 dc.l 0
''')
