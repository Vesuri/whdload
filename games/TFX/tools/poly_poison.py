"""Build the step 5 poison slave: poly_fill_040's exits load fixed junk into D0-D7/A1-A6 and
the flags, and fill what the original writes but poly_fill_040 does not with junk: the doubled
vertex list, ScanFillDown's return cell and, after a drawn polygon, exactly the edge-table
bytes GenLeft/GenRight write (bytes 0-9 of each edge record, 0-3 of the end record). A
climbing chain's partial tables are not poisoned.

  poly_poison.py OUT_DIR
"""
import sys, subprocess, shutil
from pathlib import Path
root = Path(__file__).resolve().parents[1]; out = Path(sys.argv[1]).resolve()
src = out / 'poison-src'; shutil.rmtree(src, ignore_errors=True); shutil.copytree(root / 'src', src)
p = src / 'TFXHD.s'; t = p.read_bytes().decode('latin1').replace('\r\n', '\n')


def sub(old, new):
    global t
    assert t.count(old) == 1, old; t = t.replace(old, new)


sub('        move.l  sp,(a1)                 ; as $60da2\n',
    '        move.l  sp,(a1)                 ; as $60da2\n        lea     pf_vbase(pc),a1\n        move.l  a0,(a1)+\n        move.w  d0,(a1)\n')
sub('.done:\n        lea     16(sp),sp\n        movea.l (sp)+,a0\n        rts\n', '.done:\n        lea     16(sp),sp\n        movea.l (sp)+,a0\n        bra.w   pf_poison_done\n')
sub('.fail:                                  ; as $60dec\n        lea     12(sp),sp\n        movea.l (sp)+,a0\n        rts\n',
    '.fail:                                  ; as $60dec\n        lea     12(sp),sp\n        movea.l (sp)+,a0\n        bra.w   pf_poison\n')
sub('pf_cell: dc.l 0                         ; $6c4c0\n', '''pf_cell: dc.l 0                         ; $6c4c0
pf_vbase: dc.l 0
pf_vn: dc.w 0
pf_poison_done:                         ; the edge-table bytes the original writes
        movea.l pf_recip(pc),a1
        lea     -884(a1),a1             ; left table ($62afc)
        lea     pf_left(pc),a2
        bsr.b   .records
        movea.l pf_recip(pc),a1
        lea     -442(a1),a1             ; right table ($62cb6)
        lea     pf_right(pc),a2
        bsr.b   .records
        bra.b   pf_poison
.records:
        move.l  #$deadbeef,(a1)         ; lines and x high word (end record: all it writes)
        tst.w   (a2)
        beq.b   .end
        move.l  #$deadbeef,4(a1)
        move.w  #$beef,8(a1)
        lea     26(a1),a1
        lea     12(a2),a2
        bra.b   .records
.end:
        rts
pf_poison:
        movea.l pf_vbase(pc),a1
        move.w  pf_vn(pc),d7
        lea     (a1,d7.w*4),a1          ; the doubled copy
        bra.b   .copy_next
.copy:
        move.l  #$c0dedead,(a1)+
.copy_next:
        dbf     d7,.copy
        movea.l pf_cell(pc),a1
        move.l  #$00fa1100,(a1)
        move.l  #$d0d0d0d0,d0
        move.l  #$d1d1d1d1,d1
        move.l  #$d2d2d2d2,d2
        move.l  #$d3d3d3d3,d3
        move.l  #$d4d4d4d4,d4
        move.l  #$d5d5d5d5,d5
        move.l  #$d6d6d6d6,d6
        move.l  #$d7d7d7d7,d7
        movea.l #$a1a1a1a1,a1
        movea.l #$a2a2a2a2,a2
        movea.l #$a3a3a3a3,a3
        movea.l #$a4a4a4a4,a4
        movea.l #$a5a5a5a5,a5
        movea.l #$a6a6a6a6,a6
        move.w  #$1f,ccr
        rts
''')
p.write_bytes(t.replace('\n', '\r\n').encode('latin1'))
# The poisoned TFXHD.s through common/build.sh as BUILD=poison (tmp/build/poison/TFX.Slave);
# its includes are unchanged, so src/ supplies them.
import os
subprocess.run([str(root.parents[1] / 'common/build.sh'), 'poison'], check=True, cwd=root,
               env=dict(os.environ, VARIANT='TFX', SOURCE=str(p), VASM_EXTRA='-L ' + str(out / 'poly-poison.lst')))
shutil.copyfile(root / 'tmp/build/poison/TFX.Slave', out / 'poly-poison.slave')
print('built', out / 'poly-poison.slave')
