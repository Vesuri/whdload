#!/usr/bin/env python3
# Full instruction trace of the live elapsed-time 20 ms diagnostic, taken after
# the scheduler has accumulated debt (so it never idles in its wait loop).
from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];fields=int(os.environ.get('FIELDS','48'));start_loop=int(os.environ.get('START_LOOP','132'));out=root/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(WARP='1',WINDOW='none',WHD_ARGS=os.environ.get('WHD_ARGS','CUSTOM1=1'),DETERMINISTIC='1',FSUAE=str(root/'tmp/step3/fs-uae'))
s=Server('ff1measure',root=str(root),profile_window=False);log=[];result={'name':name,'trace_fields':fields,'start_loop':start_loop,'slave':os.environ['SLAVE']}
try:
 g=s.boot()
 def cmd(c,timeout=180):
  v=g.cmd(c,timeout=timeout);log.append(c+'\n'+v);return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):cmd(f'dump binary memory tmp/step5/{name}/{label}.bin 0 0x80000')
 cmd('break *0x65606');cmd('ignore $bpnum 119');v=cmd('continue');assert 'Breakpoint' in v,v
 assert val('*(unsigned short*)0x1bee8')==1
 assert cmd('monitor warp-status')=='warp=1';cmd('monitor warp 0');cmd('ignore $bpnum 4');assert 'Breakpoint' in cmd('continue')
 assert cmd('monitor warp-status')=='warp=0'
 cmd('delete');cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
 if start_loop>125:
  cmd(f'ignore $bpnum {start_loop-126}');assert 'Breakpoint' in cmd('continue')
 dump('start');cmd('delete')
 cmd(f'monitor profile {fields} "" "{out}/detail.bin"',timeout=1800)
 dump('end');assert cmd('monitor warp-status')=='warp=0'
 result['end_state']={n:val(f'*(unsigned short*){a}') for n,a in [('demo',0x1bee8),('segment',0x6a60a),('speed',0x2275a)]}
 result['slave_sha256']=hashlib.sha256(Path(os.environ['SLAVE']).read_bytes()).hexdigest()
 for f in ('launch.json','fsuae.log'):shutil.copy(root/'amiga/.run'/f,out/f)
 result['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest();result['status']='complete'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'complete',result['end_state'],flush=True)
except Exception as e:
 result['status']='failed';result['error']=repr(e);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');raise
finally:
 try:
  (out/'capture.log').write_text('\n'.join(log))
 finally:
  if s.g:s.g.p.kill()
  try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
