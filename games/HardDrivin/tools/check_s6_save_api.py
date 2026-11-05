import os,time,json,shutil
from capture_demo import ROOT,RUN,command
from capture_session import Session
name='s6-save-api-'+os.environ.get('SAVE_PROBE_VERSION','20');os.chdir(ROOT);out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/save-probe.slave',out/'slave.slave')
s=Session(out,'a1200-020',out/'slave.slave',0);s.env['WHD_ARGS']='WRITEDELAY=0';s.env['SWAP_ONLY']='1'
try:
 s.start(tag='probe');f=RUN/'dh1/data/save-probe.dat'
 for _ in range(20):
  if f.exists():break
  time.sleep(1)
 r=dict(written=f.exists(),no_game_code=True,write_cache=True,whdload=os.environ.get('WHDLOAD_BINARY'))
 if f.exists():assert f.read_bytes()==b'Z'*380
 else:(out/'registers.txt').write_text(command('stop'))
 (out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.close()
