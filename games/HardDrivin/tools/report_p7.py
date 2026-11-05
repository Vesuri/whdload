from pathlib import Path
import json,hashlib
root=Path('tmp/prof')
phases=['hook10ed4','loop-body','07c32 controls','108a2','10f52 replay/hook','0d960 camera+record','0d40e traffic','0cda4 physics']
report={'profile':'a1200-020','gated':False,'windows':{}}
for w,field in [('a',1),('b',4000)]:
 dirs=[root/f'p7-{w}-{state}' for state in ['off','on']];meta=[json.loads((d/'metadata.json').read_text()) for d in dirs];cost=[json.loads((d/'frame-budget.json').read_text()) for d in dirs]
 for key in ['slave_sha256','emulator_sha256','game_sha256']:assert meta[0][key]==meta[1][key],(w,key)
 configs=[dict(m['configuration']) for m in meta]
 assert configs[0].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=0';assert configs[1].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=1';assert configs[0]==configs[1]
 for m in meta:
  assert m['layout']['profile']=='a1200-020' and m['configuration']['CPU']=='68EC020'
  assert m['configuration']['CHIP_KB']=='2048' and m['configuration']['FAST_KB']=='4096'
  assert m['trace_window']['fields']==500 and m['trace_window']['first_full_race_field']==field
 assert meta[0]['trace_window']['listing_sha256']==meta[1]['trace_window']['listing_sha256']
 for d,m in zip(dirs,meta):
  assert hashlib.sha256((d/'slave.slave').read_bytes()).hexdigest()==m['slave_sha256']
  assert hashlib.sha256((d/'slave.lst').read_bytes()).hexdigest()==m['trace_window']['listing_sha256']
  assert (d/'trace.bin.zst').is_file() and (d/'trace.sha256').is_file() and not (d/'trace.bin').exists()
 off,on=cost;delta={k:on['phases'].get(k,0)-off['phases'].get(k,0) for k in phases}
 extra={k:v for k,v in on['owners_all'].items() if ' | slave' in k and not any(k.startswith(p+' |') for p in phases) and not any(x in k for x in ['slave_smc','slave_blitwait'])}
 overhead=sum(delta.values())+sum(extra.values());sec=500*142102/7093790
 report['windows'][w]={'first_field':field,'fields':500,'seconds':sec,'matched':True,'phase_delta_ms':delta,'outside_simulation_slave_ms':extra,'overhead_ms':overhead,'original_frame_share_percent':overhead/off['mean_frame_ms']*100,'equal_scene_cost_loss_percent':100*overhead/(off['mean_frame_ms']+overhead),'off':{'swaps':off['swaps'],'complete_frames':off['complete_frames'],'mean_frame_ms':off['mean_frame_ms'],'fps':off['swaps']/sec,'polygons_per_frame':off['entries_per_frame']['polyfill'],'physics_entries_per_frame':off['entries_per_frame']['physics']},'on':{'swaps':on['swaps'],'complete_frames':on['complete_frames'],'mean_frame_ms':on['mean_frame_ms'],'fps':on['swaps']/sec,'polygons_per_frame':on['entries_per_frame']['polyfill'],'physics_entries_per_frame':on['entries_per_frame']['physics']}}
report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src').glob('*.s')}
report['scope']='Reported, not gated. Emulated PAL time. Existing conservative phase-difference formula plus full outside-simulation slave costs, including native-equivalent divider work. Raw FPS is scene-dependent, not equal-scene performance or simulation-speed acceptance. Cost-loss percentage is an accounting estimate, not a measured equal-scene FPS result.'
(root/'p7-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['windows'],indent=2))
