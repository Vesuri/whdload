from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-lane-scan-layout-source';shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'physics_aux.s';s=p.read_text();old=' jsr (resload_FlushCache,a2)\n rts\n cnop 0,2';assert s.count(old)==1
s=s.replace(old,' jmp aux_lane_scan_init(pc)\n nop\n cnop 0,2',1)
s+='''
; Appended helper keeps every existing hot code/copy address unchanged.
aux_lane_scan_init:
 lea $8d970,a0
 lea aux_lane_scan_body(pc),a1
 moveq #56,d0
.copy:
 move.w (a0)+,(a1)+
 dbf d0,.copy
 IFD C_LANE_SCAN_CONTROL
 bra.s .done
 ELSE
 nop
 ENDC
 lea aux_lane_scan(pc),a0
 move.w #$4ef9,$8d966
 move.l a0,$8d968
.done:
 jsr (resload_FlushCache,a2)
 rts
aux_lane_scan:
 move.b $71(a1),d7
 subq.w #1,d1
 lea $8d012,a6
aux_lane_scan_body:
 ds.b $72
''';p.write_text(s)
(dst/'lane-scan-layout.patch').write_text(''.join(difflib.unified_diff((src/'physics_aux.s').read_text().splitlines(True),s.splitlines(True),fromfile='physics_aux.s',tofile='physics_aux.s')))
control=root/'tmp/c-lane-scan-layout-control-source';shutil.copytree(dst,control,dirs_exist_ok=True);p=control/'physics_aux.s';p.write_text('C_LANE_SCAN_CONTROL = 1\n'+p.read_text())
