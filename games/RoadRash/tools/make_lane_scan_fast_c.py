from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-lane-scan-source';shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'physics_aux.s';s=p.read_text();needle=' IFD VERIFY_C_PHYSICS_AUX_CONTROL\n bra.w .done';assert needle in s
s=s.replace(needle,''' lea $8d970,a0
 lea aux_lane_scan_body(pc),a1
 moveq #56,d0
.copy_lane_scan:
 move.w (a0)+,(a1)+
 dbf d0,.copy_lane_scan
'''+needle,1)
needle=' move.l a0,$8da5e\n.done:';assert needle in s
s=s.replace(needle,''' move.l a0,$8da5e
 IFD C_LANE_SCAN_CONTROL
 bra.s .lane_done
 ELSE
 nop
 ENDC
 lea aux_lane_scan(pc),a0
 move.w #$4ef9,$8d966
 move.l a0,$8d968
.lane_done:
.done:''',1)
s+='''
; Identical native lane scan, with its mutable table kept at the native address.
; Only the initial PC-relative LEA becomes absolute. All body branches stay local.
aux_lane_scan:
 move.b $71(a1),d7
 subq.w #1,d1
 lea $8d012,a6
aux_lane_scan_body:
 ds.b $72
''';p.write_text(s)
(dst/'lane-scan.patch').write_text(''.join(difflib.unified_diff((src/'physics_aux.s').read_text().splitlines(True),s.splitlines(True),fromfile='physics_aux.s',tofile='physics_aux.s')))
control=root/'tmp/c-lane-scan-control-source';shutil.copytree(dst,control,dirs_exist_ok=True);p=control/'physics_aux.s';p.write_text('C_LANE_SCAN_CONTROL = 1\n'+p.read_text())
