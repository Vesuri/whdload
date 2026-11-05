from pathlib import Path
import subprocess,os
root=Path(__file__).resolve().parents[1];src=root/'src';out=root/'tmp/build'
s=(src/'timing-live-loop.i').read_text().replace(' move.w #$0040,$dff09a', ''' move.w $dff002,d0
 andi.w #$0400,d0
 lea timing_blitter_dma(pc),a0
 move.w d0,(a0)
 move.w #$8400,$dff096
 move.w #$0040,$dff09a''')
s=s.replace('timing_blitter_release:\n bsr timing_display_drain\n move.l d0,-(sp)', '''timing_blitter_release:
 bsr timing_display_drain
 move.l d0,-(sp)
 move.w #$0400,$dff096
 move.w timing_blitter_dma(pc),d0
 beq .dma_restored
 move.w #$8400,$dff096
.dma_restored:''')
s+='\ntiming_blitter_dma: dc.w 0\n';(out/'bltpri-loop.i').write_text(s)
slave=(src/'GunshipHD.s').read_text().replace('include "timing-live-loop.i"','include "'+str(out/'bltpri-loop.i')+'"');(out/'bltpri.s').write_text(slave)
cmd=[os.environ['VASM'],'-DVERIFY=1','-DTIMING_RUNTIME=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym']
for p in [Path(os.environ['AMIGA_INCLUDE']),Path(os.environ['WHDLOAD'])/'Include',Path(os.environ['WHDLOAD'])/'Src',Path(os.environ['WHDLOAD'])/'Src/sources',Path(os.environ['AMIGA_SHARE'])/'ndk/Include_I',src]:cmd+=['-I'+str(p)]
cmd+=['-L',str(out/'Gunship-d5-bltpri.slave.lst'),'-o',str(out/'Gunship-d5-bltpri.slave'),str(out/'bltpri.s')];subprocess.run(cmd,cwd=src,check=True)
