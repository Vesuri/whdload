#!/usr/bin/env python3
from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct,time
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];fields=int(os.environ.get('FIELDS','1000'));mode=os.environ.get('OBSERVE','survey');out=root/'tmp/step4'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=os.environ.get('SLAVE',str(root/'tmp/build/step4-pause/pause.slave')),WARP='1',WINDOW='none',WHD_ARGS=os.environ.get('WHD_ARGS','CUSTOM1=0'),DETERMINISTIC='1',FSUAE=str(root/'tmp/step3/fs-uae'))
s=Server('ff1measure',root=str(root),profile_window=False);log=[];result={'name':name,'protocol':'native_pause_consumer_fixture_fields','observed_fields':100,'extra_args':os.environ.get('EXTRA_ARGS','')}
try:
 g=s.boot()
 def cmd(c,timeout=180):
  v=g.cmd(c,timeout=timeout);log.append(c+'\n'+v);return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):cmd(f'dump binary memory tmp/step4/{name}/{label}.bin 0 0x80000')
 cmd('break *0x65606');cmd('ignore $bpnum 119');v=cmd('continue');assert 'Breakpoint' in v,v
 dump('update120');result['demo']=val('*(unsigned short*)0x1bee8');assert result['demo']==1
 result['warp_before']=cmd('monitor warp-status');assert result['warp_before']=='warp=1';cmd('monitor warp 0');cmd('ignore $bpnum 4');assert 'Breakpoint' in cmd('continue')
 dump('anchor');result['warp_after']=cmd('monitor warp-status');assert result['warp_after']=='warp=0'
 b=(out/'anchor.bin').read_bytes();assert b[0x65600:0x65606]==bytes.fromhex('4eb900067120'),b[0x65600:0x65606].hex()
 result['anchor_state']={n:struct.unpack_from('>H',b,a)[0] for n,a in [('demo',0x1bee8),('segment',0x6a60a),('speed',0x2275a),('countdown',0x66f94),('field_counter',0x24ad2)]}
 cmd('delete');cmd('break *0x65174');assert 'Breakpoint' in cmd('continue');dump('before_pause')
 cmd('delete');cmd('break *0x6542c');v=cmd('continue');assert 'Breakpoint' in v,v
 dump('pause_start');result['pause_pc']=val('$pc')
 cmd('delete');result['capture_reply']=cmd(f'monitor census 100 "" "{out}/window.jsonl"');dump('pause_end')
 result['paused_end_pc']=val('$pc');result['warp_end']=cmd('monitor warp-status');assert result['warp_end']=='warp=0'
 cmd('break *0x65174');v=cmd('continue');assert 'Breakpoint' in v,v
 dump('resumed_loop')
 result['end_state']={'demo':val('*(unsigned short*)0x1bee8'),'mode':val('*(unsigned short*)0x1c1c2')}
 for f in ('launch.json','fsuae.log'):shutil.copy(root/'amiga/.run'/f,out/f)
 result['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest();result['status']='complete'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'complete',result['end_state'],flush=True)
except Exception as e:
 result['status']='failed';result['error']=repr(e);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');raise
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
