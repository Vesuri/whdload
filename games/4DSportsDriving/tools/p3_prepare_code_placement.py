from pathlib import Path
import shutil
src=Path('src').resolve()
for bank in ('chip','fast'):
 dst=Path('tmp/fixtures/p3-code-'+bank)/'source';assert not dst.exists();shutil.copytree(src,dst)
 p=dst/'raster.s';s=p.read_text();end=s.index('; Reject slow expansion');a=s[:end].replace('d0-d1/a0-a1/a6','d0-d1/a0-a2/a6')
 old='.done:\n movem.l (sp)+,d0-d1/a0-a2/a6\n rts'
 assert old in a
 block='''.done:
 ; Ignored placement diagnostic: same copied PIC kernel and trampoline in both cells.
 lea raster_solid_fast(pc),a0
 lea raster_code_copy(pc),a1
 move.l a0,(a1)
 move.l raster_buffer(pc),d0
 beq .copy_done
 move.l 4.w,a6
 move.l #raster_solid_fast_end-raster_solid_fast,d0
 moveq #MEMF_BANK,d1
 jsr _LVOAllocMem(a6)
 tst.l d0
 beq .copy_done
 lea raster_code_copy(pc),a1
 move.l d0,(a1)
 move.l d0,a1
 lea raster_solid_fast(pc),a0
 move.w #(raster_solid_fast_end-raster_solid_fast)/2-1,d0
.copy_kernel:
 move.w (a0)+,(a1)+
 dbra d0,.copy_kernel
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.copy_done:
 movem.l (sp)+,d0-d1/a0-a2/a6
 rts
'''.replace('MEMF_BANK','MEMF_CHIP' if bank=='chip' else 'MEMF_FAST')
 a=a.replace(old,block);s=a+s[end:];assert s.count(' bra raster_solid_fast\n')==1;s=s.replace(' bra raster_solid_fast\n',' move.l raster_code_copy(pc),-(sp)\n rts\n');s+='\n even\nraster_code_copy: dc.l 0\n';p.write_text(s)
