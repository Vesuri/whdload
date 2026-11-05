#!/usr/bin/env python3
"""Named Phase 6 driving differences, with no arbitrary whole-state masks."""
import argparse,json
from pathlib import Path
from phase3_decode import decode
p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('--output',type=Path);p.add_argument('--assert-core',action='store_true');p.add_argument('--match-native-fields',action='store_true');a=p.parse_args()
keys=['native_field','pause','active_fields','countdown','lap_ticks','completed_lap_ticks','lap','race_tick_counter','race_running','status','inhibit','demo','opponents','speed','rpm','gear','fraction','lateral','steering','yaw','road_curve','consumed_joy','input_activity','condition','heat','rng','segment']+[f'AI_{n}_{i}' for i in range(10) for n in ['segment','fraction','speed','lateral','cooldown','position_pointer']]
keys += ['speed_sum','max_speed','statistics_sum','last_lap','lap_display_hold','wheelspin','gear_moving','clutch','gear_lever_x','gear_lever_y','idle_timer','collision_partner','collision_frame','spin','brake_parameter','grip_parameter','distance_base','distance_q8','finish']
def rows(root):
 m=json.loads((root/'metadata.json').read_text());return [decode(f.read_bytes(),m) for f in sorted((root/'state').glob('[0-9]*.bin'))]
l=rows(a.left);r=rows(a.right)
coverage={}
if a.match_native_fields:
 ld={v['native_field']:v for v in l};rd={v['native_field']:v for v in r}
 assert len(ld)==len(l) and len(rd)==len(r)
 common=sorted(ld.keys() & rd.keys());assert common
 missing=[sorted(ld.keys()-rd.keys()),sorted(rd.keys()-ld.keys())]
 # Sparse lap captures can stop at the actual finish or the next six-field
 # sample. Permit only one trailing endpoint per side, never missing interior
 # samples; record both endpoints and compare every shared native field.
 assert all(len(xs)<=1 and all(common[-1]<v<=common[-1]+6 for v in xs) for xs in missing)
 coverage={'source_samples':[len(l),len(r)],'unmatched_native_fields':missing,'first_matched_field':common[0],'last_matched_field':common[-1]}
 l=[ld[i] for i in common];r=[rd[i] for i in common]
else:assert len(l)==len(r)
res={'fields':len(l),'differences':{},'coverage':coverage}
for k in keys:
 dif=[(i,x[k],y[k]) for i,(x,y) in enumerate(zip(l,r)) if x[k]!=y[k]]
 if dif:res['differences'][k]={'first':dif[0],'last':dif[-1],'count':len(dif),'max_abs':max(abs(x-y) for i,x,y in dif)}
for name,rs in [('left',l),('right',r)]:res[name]={'final':{k:rs[-1][k] for k in keys},'periods':sorted(set(x['period'] for x in rs)),'statuses':sorted(set(x['status'] for x in rs))}
print(json.dumps(res,indent=2))
if a.output:a.output.write_text(json.dumps(res,indent=2)+'\n')
if a.assert_core:assert not res['differences'],res['differences']
