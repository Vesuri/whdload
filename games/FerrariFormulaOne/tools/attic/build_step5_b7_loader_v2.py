from pathlib import Path
import subprocess,struct,os
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b7-loader-v2';o.mkdir(parents=True,exist_ok=True)
s=(r/'tmp/build/release/FerrariFormulaOne_WHD.s').read_bytes().decode('latin1')
s=s.replace('\tdc.l\tTAG_DONE','\tdc.l\tWHDLTAG_CUSTOM2_GET\nFF1PublicEnabled\tdc.l 0\n\tdc.l\tTAG_DONE',1)
s=s.replace('\tjsr\t_LVOLoadSeg(a6)','\tbsr.w FF1PublicBoot\n\tjsr\t_LVOLoadSeg(a6)\n\tmove.l d0,FF1PublicRoot',1) # PIC fix below
s=s.replace('\tmove.l d0,FF1PublicRoot','\tlea FF1PublicRoot(pc),a0\n\tmove.l d0,(a0)')
# Keep the ordinary path unchanged. Public mode resolves the official slave's
# three race repairs from the native hunk table, not from first-hunk offsets.
pos=s.index('.patchhunk',s.index('PLGAME\tPL_START'))
pos=s.index('\n.patchhunk',pos)
end=s.index('; check if it is the "Race" hunk',pos)
s=s[:end]+''' move.l d1,-(sp)
 move.l FF1PublicEnabled(pc),d1
 movem.l (sp)+,d1
 beq.w .legacy_layout
 cmpi.l #$22f30,(a3)
 bne.w .no
 movem.l d0-d7/a0-a6,-(sp)
 move.l a4,a0
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a0
 lea .patch(pc),a1
 lea fixtiming(pc),a2
 move.l NOTIMINGFIX(pc),d0
 bsr.w FF1PatchPublicRace
 lea FF1PublicPatchError(pc),a0
 move.l d0,(a0)
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $4e71,$4e71,$4e71 ; B7 after-patch integration slot
 bra.w .no
.legacy_layout:
'''+s[end:]
s=s.replace('\tjsr\t4(a3)','FF1PublicCallSite equ *\n\tjsr\t4(a3)',1)
s+='''
FF1PublicPatchError: dc.l 0
FF1PublicBoot:
 movem.l d0-d7/a0-a6,-(sp)
 move.l FF1PublicEnabled(pc),d0
 beq.b .done
 lea FF1PublicPool(pc),a0
 move.l _expmem(pc),a1
 adda.l #$40000,a1
 move.l #$80000,d0
 moveq #1,d1
 move.l a1,d2
 cmpi.l #$200000,d2
 blo.b .attrs
 cmpi.l #$980000,d2
 bhi.b .attrs
 moveq #5,d1
.attrs:
 bsr.w FF1PublicPoolOpen
 tst.l d0
 bne.b .done
 lea FF1PublicCallSite(pc),a0
 move.w #$6100,(a0)
 move.w #FF1PublicCall-FF1PublicCallSite-2,2(a0)
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1PublicPool: ds.l 2
FF1PublicRoot: dc.l 0
FF1PublicMarker: dc.b 'FF1B7PUBLICROOT',0,0
 even
 include "FerrariFormulaOne_PublicMemory.s"
 include "FerrariFormulaOne_PublicLoader.s"
 include "FerrariFormulaOne_PublicStack.s"
'''
(o/'FerrariFormulaOne_WHD.s').write_bytes(s.encode('latin1'))
for name,target in [('SOURCES:Include',Path(os.environ['WHDLOAD'])/'Include'),('Sources:whdload',Path(os.environ['WHDLOAD'])/'Src/sources/whdload'),('lvo',r/'tmp/build/release/lvo')]:
 p=o/name
 if not p.exists():p.symlink_to(target,target_is_directory=True)
subprocess.run([os.environ['VASM'],'-DFF1_PUBLIC_MEMORY=1','-DFF1_PUBLIC_LOADER=1','-DFF1_PUBLIC_STACK=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+str(o),'-I'+str(r.parents[1]/'Games'),'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK'],'-L','build.list','-o','FerrariFormulaOne.slave','FerrariFormulaOne_WHD.s'],cwd=o,check=True,stdout=subprocess.DEVNULL)
b=bytearray((o/'FerrariFormulaOne.slave').read_bytes());assert b[64:68]==bytes.fromhex('00040000');b[64:68]=struct.pack('>I',0xc0000);(o/'FerrariFormulaOne.slave').write_bytes(b);print('Built native-loader public-memory diagnostic')
