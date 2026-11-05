import os,sys,time,json,subprocess,signal,shutil
from pathlib import Path
root=Path.cwd();dest=root/'tmp/prof/p7-live';dest.mkdir(exist_ok=False);source=root/'src'
def owned():
 p=root/'tmp/run/default/.run/fsuae.pid'
 if not p.exists():return False
 pid=int(p.read_text());q=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
 dirs=[x[1:] for x in q.stdout.splitlines() if x.startswith('n')]
 if not dirs:return False
 assert len(dirs)==1 and Path(dirs[0]).is_relative_to(root),(pid,dirs)
 return pid
for phase,delta in [('nominal',0),('minus64',-64),('plus64',64)]:
 src=source
 if delta:
  src=dest/(phase+'-source');shutil.copytree(source,src)
  p=src/'simulation_verify.s';s=p.read_text();needle=' move.w #1,(a0)\n IFD SIM_FIXTURE_GEARS'
  assert needle in s
  s=s.replace(needle,f' move.w #1,(a0)\n add.l #{delta},-$926(a4)\n lea -$8b6(a4),a0\n moveq #3,d1\n.phase_wheels:\n add.w #{delta//64},(a0)\n lea 6(a0),a0\n dbra d1,.phase_wheels\n IFD SIM_FIXTURE_GEARS',1);p.write_text(s)
 env=dict(os.environ,GAME_SOURCE=str(src),VERIFY='1',SIM_A4000='1',SIM_STARTUP_TESTS='0',SIM_FIXTURE_OFFROAD='1',SIM_FIXTURE_TURN_SECONDS='30',SIM_FIXTURE_SAMPLES='64',SIM_FIXTURE_SAMPLE_HZ='5',CPU='68020',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',WHD_ARGS='CUSTOM2=0',GAME=str(root/'tmp/fixtures/natural-crest'),DEBUG_PORT='2471',WARP='1',SLAVE=str(root/'tmp/build/4DSportsDriving-verify.slave'))
 with (dest/(phase+'.log')).open('w') as log:
  subprocess.run(['tools/build.sh'],env=env,stdout=log,stderr=log,check=True)
  assert not owned(),'Existing owned emulator must be closed explicitly first'
  deadline=time.monotonic()+180
  try:
   for cmd in [[sys.executable,'tools/quick_start.py',str(dest/phase),'--simulation','50','--tick','5'],[sys.executable,'tools/bridge_probe.py',str(dest/phase),'16']]:
    subprocess.run(cmd,env=env,stdout=log,stderr=log,check=True,timeout=max(1,deadline-time.monotonic()))
  finally:
   if owned():
    try:subprocess.run([sys.executable,'tools/driving.py','quit'],env=env,stdout=log,stderr=log,timeout=8,check=True)
    finally:
     if (pid:=owned()):os.kill(pid,signal.SIGTERM)
 rows=json.loads((dest/phase/'bridge.json').read_text())['rows'];ref={r['tick']:r for r in json.loads((root/f'tmp/prof/p7-session1/combined-{phase}.json').read_text())['rows']}
 for r in rows:
  e=ref[r['tick']]
  assert all(r[k]==e[k] for k in ('x','y','z','pitch','speed')) and [r[f'w{i}'] for i in range(4)]==e['flags'],(phase,r,e)
 assert len(rows)==795
 (dest/phase/'offline-equivalence.json').write_text(json.dumps(dict(equal_body_records=795,first=6,last=800,fields=['x','y','z','pitch','speed','w0','w1','w2','w3']))+'\n')
 print(phase,'795/795 exact',flush=True)
