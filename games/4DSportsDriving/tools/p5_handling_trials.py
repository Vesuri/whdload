import os,sys,json,subprocess,hashlib
from pathlib import Path
p=Path('tmp/prof/p5-handling');p.mkdir(exist_ok=True)
f=Path('tmp/prof/natural-crest-criteria.json');before=hashlib.sha256(f.read_bytes()).hexdigest();assert before=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
env=dict(os.environ,COUPLED_REPORT_DIR=str(p));log=(p/'trials.log').open('w')
for phase in ('nominal','minus64','plus64'):
 for mode in ('baseline','extension-linear-control','exponential-extension','native-geometric-pitch-control','native-geometric-pitch'):
  subprocess.run([sys.executable,'tools/coupled_course_check.py',mode,phase],env=env,stdout=log,stderr=log,check=True,timeout=120)
  print(phase,mode,'complete',flush=True)
assert hashlib.sha256(f.read_bytes()).hexdigest()==before
