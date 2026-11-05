from pathlib import Path
import hashlib,json
root=Path('tmp/prof')
report={'status':'P4 incomplete', 'helper_limit_ms':1.4,'native_extra_limit_ms':1.0,'windows':{}}
for w,field in [('a',1),('b',4000)]:
 dirs=[root/f'p4-motion-{w}-{state}' for state in ['off','on']]
 meta=[json.loads((p/'metadata.json').read_text()) for p in dirs]
 for key in ['slave_sha256','emulator_sha256','game_sha256']:
  assert meta[0][key]==meta[1][key],(w,key)
 for m in meta:
  assert m['trace_window']['fields']==500 and m['trace_window']['first_full_race_field']==field
 assert meta[0]['trace_window']['listing_sha256']==meta[1]['trace_window']['listing_sha256']
 configs=[dict(m['configuration']) for m in meta]
 assert configs[0].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=0'
 assert configs[1].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=1'
 assert configs[0]==configs[1]
 budgets=[json.loads((p/'frame-budget.json').read_text()) for p in dirs]
 off,on=budgets
 assert all(b['fields']==500 and b['complete_frames']>0 for b in budgets)
 helper=on['physics_slave_ms'];native_extra=on['physics_native_ms']-off['physics_native_ms']
 report['windows'][w]={'helper_ms':helper,'helper_excess_ms':helper-1.4,'helper_passed':helper<=1.4,'native_ms':on['physics_native_ms'],'original_native_ms':off['physics_native_ms'],'native_extra_ms':native_extra,'native_passed':native_extra<=1.0,'off_frames':off['complete_frames'],'on_frames':on['complete_frames'],'identical_build_emulator_game_and_configuration_except_custom1':True}
report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src').glob('*.s'))}
report['scope']='Matched builds, inputs and ten-second windows; diverging trajectories prevent interpreting raw frame means as equal-scene FPS.'
(root/'p4-motion-pair-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['windows'],indent=2))
