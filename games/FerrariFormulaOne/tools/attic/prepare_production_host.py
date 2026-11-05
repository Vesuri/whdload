from pathlib import Path
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games'
s=(r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne_WHD.s').read_text(encoding='latin1')
s=s.replace(';DEBUG ; local release build',';DEBUG ; enable only for a local diagnostic build')
s=s.replace('Version 1.01 (07.08.2016)','Version 1.02 (performance mode opt-in)')
s=s.replace('"C1:B:Disable Timing Fix"','"C1:B:Disable Timing Fix;C2:B:Elapsed-time performance mode (SPS 0481)"')
s=s.replace('\tlea\tPLGAME_IREK(pc),a5','\tclr.l FF1PublicEnabled\n\tlea\tPLGAME_IREK(pc),a5')
s=s.replace('\tclr.l FF1PublicEnabled','\tlea FF1PublicEnabled(pc),a0\n\tclr.l (a0)')
s=s.replace(' dc.w $4e71,$4e71,$4e71 ; B7 after-patch integration slot',' bsr.w FF1Dispatch')
s=s.replace(' move.l NOTIMINGFIX(pc),d0\n bsr.w FF1PatchPublicRace',' moveq #1,d0 ; elapsed mode replaces the native timing callback\n bsr.w FF1PatchPublicRace')
s=s.replace(' move.l d0,(a0)\n move.l _resload(pc),a2\n jsr resload_FlushCache(a2)\n movem.l (sp)+,d0-d7/a0-a6',' move.l d0,(a0)\n tst.l d0\n bne.w FF1WrongVersion\n move.l _resload(pc),a2\n jsr resload_FlushCache(a2)\n movem.l (sp)+,d0-d7/a0-a6',1)
s=s.replace(' moveq #1,d1\n move.l a1,d2\n cmpi.l #$200000,d2\n blo.b .attrs\n cmpi.l #$980000,d2\n bhi.b .attrs\n moveq #5,d1\n.attrs:', ''' move.l a0,-(sp)
 move.l a1,d2
 move.l #$80000,d3
 moveq #1,d0
 moveq #2,d1
 bsr.w FF1SelectProfile
 moveq #1,d1
 cmpi.l #2,d0
 bne.b .attrs
 moveq #5,d1
.attrs:
 move.l (sp)+,a0
 move.l #$80000,d0''')
s=s.replace(' tst.l d0\n bne.b .done\n lea FF1PublicCallSite',' tst.l d0\n bne.w FF1WrongVersion\n lea FF1PublicCallSite')
s+='\n include "ProductionHost.s"\n'
(g/'FerrariFormulaOne_WHD.s').write_bytes(s.encode('latin1'))
