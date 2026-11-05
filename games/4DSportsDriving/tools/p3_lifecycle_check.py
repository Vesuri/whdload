import os,subprocess,sys
from pathlib import Path
cap=sys.argv[1]
route='p1_native_replay.py' if os.environ.get('P3_LIFECYCLE')=='replay' else 'p1_crash_finish.py'
if route=='p1_crash_finish.py':
 import json,re
 from profile_window import command
 m=json.loads((Path(cap)/'anchor.json').read_text());a=m['data_base']+0x7ffe
 command('gdb monitor key 4c 1')
 approach=[]
 for _ in range(300):
  text=command(f'gdb p /u *(unsigned int*){a-0x926:#x}')
  z=int(re.search(r'\$\d+ = (\d+)',text)[1]);approach.append(z)
  if z>=384020:break
  command('gdb monitor fields 1')
 assert 384020<=z<400000,('Crash approach missed',z)
 (Path(cap)/'crash-approach.json').write_text(json.dumps(approach))
subprocess.run([sys.executable,str(Path(__file__).with_name(route)),cap],check=True)
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_background_check.py')),cap],check=True)
