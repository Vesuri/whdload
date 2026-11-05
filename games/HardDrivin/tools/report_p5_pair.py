from pathlib import Path
import hashlib,json
root=Path('tmp/prof');phases=['hook10ed4','loop-body','07c32 controls','108a2','10f52 replay/hook'];simulation=phases+['0d960 camera+record','0d40e traffic','0cda4 physics']
report={'status':'Validated candidate; B exceeds P5 target','p5_limit_ms':0.3,'windows':{}}
for w,field in [('a',1),('b',4000)]:
 dirs=[root/f'p5-fold-{w}-{state}' for state in ['off','on']];meta=[json.loads((p/'metadata.json').read_text()) for p in dirs]
 for key in ['slave_sha256','emulator_sha256','game_sha256']:assert meta[0][key]==meta[1][key],(w,key)
 for m in meta:assert m['trace_window']['fields']==500 and m['trace_window']['first_full_race_field']==field
 assert meta[0]['trace_window']['listing_sha256']==meta[1]['trace_window']['listing_sha256']
 configs=[dict(m['configuration']) for m in meta]
 assert configs[0].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=0';assert configs[1].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=1';assert configs[0]==configs[1]
 off,on=[json.loads((p/'frame-budget.json').read_text()) for p in dirs]
 delta={k:on['phases'].get(k,0)-off['phases'].get(k,0) for k in simulation}
 extra={k:v for k,v in on['owners_all'].items() if ' | slave' in k and not any(k.startswith(p+' |') for p in simulation) and not any(x in k for x in ['slave_smc','slave_blitwait'])}
 remaining=sum(delta[k] for k in phases)+sum(extra.values());overhead=sum(delta.values())+sum(extra.values());budget=off['mean_frame_ms']*(1/.97-1)
 report['windows'][w]=dict(remaining_hooks_ms=remaining,p5_passed=remaining<=.3,p5_excess_ms=max(0,remaining-.3),phase_delta_ms=delta,other_timing_slave_ms=extra,overhead_ms=overhead,cost_budget_ms=budget,g1_numeric_passed=overhead<=min(budget,{"a":8.07,"b":3.78}[w]),plan_budget_ms={"a":8.07,"b":3.78}[w],physics_helper_ms=on['physics_slave_ms'],physics_native_extra_ms=on['physics_native_ms']-off['physics_native_ms'],off_frames=off['complete_frames'],on_frames=on['complete_frames'],off_frame_ms=off['mean_frame_ms'],on_frame_ms=on['mean_frame_ms'],off_polys=off['entries_per_frame']['polyfill'],on_polys=on['entries_per_frame']['polyfill'],matched=True)
report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src').glob('*.s'))}
report['scope']='Same section-1 main-context phase-difference metric, plus every remaining timing-slave bucket outside those phases. owners_all retains buckets below the display threshold. Raw frame means are scene-mismatched and are not equal-scene FPS evidence. No P4 exception is extended to P5.'
(root/'p5-pair-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['windows'],indent=2))
