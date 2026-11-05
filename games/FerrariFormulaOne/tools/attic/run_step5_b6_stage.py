from pathlib import Path
import os,sys,json,subprocess,hashlib
r=Path(__file__).resolve().parents[1];stage=os.environ.get('B6_STAGE','1');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());tag=f'b6-s{stage}'
def run(tool,args=[],env=None):subprocess.run([sys.executable,str(r/'tools'/tool),*args],env=env,check=True)
for profile,lo,hi in (('a1200-fast','5b2f50','5b3540'),('a1200','1b0f50','1b1540')):
 slave=r/f'tmp/build/step5-{tag}/lean/fine.slave';name=f'{profile}-{tag}-profile';out=r/f'tmp/step5/{name}'
 e=dict(os.environ,**profiles[profile],KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(slave),WHD_ARGS='CUSTOM1=1 CUSTOM2=1',START_LOOP='125')
 if not (out/'profile.json').exists():
  run('capture_step5_profile.py',[name],e)
  for tool,args in (('analyze_step5_profile.py',[]),('percar_step5_profile.py',[lo,hi]),('classify_step5_profile.py',[lo,hi])):
   with (out/(tool+'.txt')).open('w') as f:subprocess.run([sys.executable,str(r/'tools'/tool),name,*args],env=dict(os.environ,EXCLUDE_PACING='1',DROP_UPDATES='1',MAX_UPDATES='20'),stdout=f,check=True)
 print(name,json.loads((out/'profile.json').read_text())['mean_cycles'],flush=True)
 if profile=='a1200-fast':assert json.loads((out/'profile.json').read_text())['mean_cycles']<=165000,'B6 abort: re-profile before further changes'
 for variant in ('verify','lean'):
  slave=r/f'tmp/build/step5-{tag}/{variant}/fine.slave';name=f'{profile}-{tag}-matrix-{variant}-fine';out=r/f'tmp/step5/{name}'
  if (out/'result.json').exists() and json.loads((out/'result.json').read_text()).get('status')=='complete':continue
  e=dict(os.environ,**profiles[profile],KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(slave),WHD_ARGS='CUSTOM1=1 CUSTOM2=1',LEAN='1' if variant=='lean' else '0')
  run('capture_step5_b6.py',[name],e)
for tool in ('states','elapsed','replay'):
 s=(r/f'tools/analyze_step5_b5_{tool}.py').read_text().replace("ver='v5'",f"ver='s{stage}'").replace('b5-v5',tag).replace('b5-{ver}','b6-{ver}').replace('step5-'+tag+'-compact','step5-'+tag).replace('step5-b4-v4-matrix','step5-b5-v5-matrix').replace('-b4-v4-matrix','-b5-v5-matrix')
 s=s.replace('B4 versus B5','B5 versus B6').replace('B5 player','B6 player').replace('B5 simulation','B6 simulation')
 dest=r/f'tools/analyze_step5_{tag}_{tool}.py';dest.write_text(s);run(dest.name)
 report=json.loads((r/f'manifest/step5-{tag}-'+Path('unused')).read_text()) if False else json.loads((r/f'manifest/step5-{tag}-{dict(states="state",elapsed="elapsed",replay="replay")[tool]}-validation.json').read_text())
 assert report['status']=='passed',report
