"""Audit paired current-source A500 gate traces; preserve the accepted B exception."""
from pathlib import Path
import json,hashlib,sys
prefix=sys.argv[1];root=Path('tmp/prof')
phases=['hook10ed4','loop-body','07c32 controls','108a2','10f52 replay/hook','0d960 camera+record','0d40e traffic','0cda4 physics']
report={'prefix':prefix,'scope':'Full phase and sweep build. Established phase-difference accounting; raw FPS is scene-dependent. The B allowance is only the accepted 5.740 ms/frame.','windows':{}}
for w,start in [('a',1),('b',4000)]:
 dirs=[root/f'{prefix}-{w}-{x}' for x in ['off','on']];meta=[json.loads((p/'metadata.json').read_text()) for p in dirs];cost=[json.loads((p/'frame-budget.json').read_text()) for p in dirs]
 for key in ['slave_sha256','game_sha256','emulator_sha256']:assert meta[0][key]==meta[1][key]
 assert meta[0]['trace_window']['listing_sha256']==meta[1]['trace_window']['listing_sha256']
 configs=[dict(m['configuration']) for m in meta]
 assert configs[0].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=0';assert configs[1].pop('WHD_ARGS')=='CUSTOM4=0 CUSTOM1=1';assert configs[0]==configs[1]
 for p,m in zip(dirs,meta):
  assert m['trace_window']['fields']==500 and m['trace_window']['first_full_race_field']==start
  assert hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest()==m['slave_sha256']
  assert hashlib.sha256((p/'slave.lst').read_bytes()).hexdigest()==m['trace_window']['listing_sha256']
  assert json.loads((p/'trace-check.json').read_text())['passed']
 off,on=cost;delta={k:on['phases'].get(k,0)-off['phases'].get(k,0) for k in phases}
 extra={k:v for k,v in on['owners_all'].items() if ' | slave' in k and not any(k.startswith(p+' |') for p in phases) and not any(x in k for x in ['slave_smc','slave_blitwait'])}
 native_extra=sum(on.get('native_timing_extra',{}).values())-sum(off.get('native_timing_extra',{}).values())
 overhead=sum(delta.values())+sum(extra.values())+native_extra;limit={'a':8.07,'b':5.740}[w];seconds=500*142102/7093790
 r={'phase_delta_ms':delta,'outside_timing_ms':extra,'overhead_ms':overhead,'outside_native_timing_ms':native_extra,'accepted_limit_ms':limit,'within_accepted_limit':overhead<=limit,'sweep_ms':on['owners_all'].get('0cda4 physics | slave_sweep',0)}
 for state,c in zip(['off','on'],cost):r[state]={k:c[k] for k in ['mean_frame_ms','swaps','complete_frames']};r[state].update(fps=c['swaps']/seconds,polygons=c['entries_per_frame']['polyfill'])
 report['windows'][w]=r
report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src').glob('*.s')}
report['disabled_passed']=all(json.loads((root/f'{prefix}-{w}-off/disabled.json').read_text())['passed'] for w in ['a','b'])
report['ordinary_byte_identical']=Path(f'tmp/build/{prefix}-normal.slave').read_bytes()==Path('tmp/build/s2-final-normal.slave').read_bytes()
report['branch_audit']=json.loads(Path(f'tmp/{prefix}-branches.json').read_text())
report['g1_within_accepted_limits']=all(r['within_accepted_limit'] for r in report['windows'].values())
Path(f'tmp/{prefix}-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['windows'],indent=2))
