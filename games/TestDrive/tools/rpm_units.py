#!/usr/bin/env python3
"""Build a scratch VERIFY unit runner for the actual production dial helpers."""
import os,shutil,subprocess
from pathlib import Path
from harness import ROOT
out=ROOT/'tmp/rpm-needle/units';out.mkdir();stage=out/'source';shutil.copytree(ROOT/'src',stage)
p=stage/'simulation-verify.s';s=p.read_text().replace('    bsr verify_units\n','    bsr verify_units\n    bsr rpm_units\n',1)
s+='''
rpm_units:
    movem.l d0-a6,-(sp)
    lea rpm_unit_frame(pc),a5
    lea rpm_unit_data(pc),a4
    adda.l #26340,a4
    moveq #0,d7
.car
    move.w d7,8(a5)
    bsr instrument_car
    lea rpm_unit_expected(pc),a2
    move.w d7,d0
    add.w d0,d0
    move.w (a2,d0.w),d3
    cmp.w instrument_limit(pc),d3
    beq.b .inputs
    bsr rpm_unit_fail
.inputs
    moveq #0,d6
.input
    move.w d6,-26340(a4)
    move.l #$99aa0000,d0
    bsr instrument_rpm
    blt.b .flags_ok
    bsr rpm_unit_fail
.flags_ok
    move.w d6,d1
    cmp.w d3,d1
    ble.b .expected
    move.w d3,d1
.expected
    cmp.w d1,d0
    beq.b .value_ok
    bsr rpm_unit_fail
.value_ok
    swap d0
    cmp.w #$99aa,d0
    beq.b .high_ok
    bsr rpm_unit_fail
.high_ok
    cmp.w -26340(a4),d6
    beq.b .state_ok
    bsr rpm_unit_fail
.state_ok
    lea rpm_unit_count(pc),a0
    addq.l #1,(a0)
    addq.w #1,d6
    bne.b .input
    addq.w #1,d7
    cmp.w #5,d7
    bcs.b .car
    movem.l (sp)+,d0-a6
    rts
rpm_unit_fail:
    lea rpm_unit_failures(pc),a0
    addq.l #1,(a0)
    rts
rpm_unit_expected: dc.w 7000,10000,7000,9000,0
rpm_unit_frame: dcb.w 5,0
rpm_unit_data: dcb.w 6,0
    dc.w 15000
rpm_unit_count: dc.l 0
rpm_unit_failures: dc.l 0
''';p.write_text(s)
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True)
