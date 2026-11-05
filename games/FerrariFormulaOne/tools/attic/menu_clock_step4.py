#!/usr/bin/env python3
from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct,time
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];fields=int(os.environ.get('FIELDS','1000'));mode=os.environ.get('OBSERVE','survey');out=root/'tmp/step4'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=os.environ.get('SLAVE',str(root/'tmp/build/release/FerrariFormulaOne.slave')),WARP='1',WINDOW='none',WHD_ARGS=os.environ.get('WHD_ARGS','CUSTOM1=0'),DETERMINISTIC='1',FSUAE=str(root/'tmp/step3/fs-uae'))
s=Server('ff1measure',root=str(root),profile_window=False);log=[];result={'name':name,'protocol':'startup_clock_fields','observed_fields':600,'extra_args':os.environ.get('EXTRA_ARGS','')}
try:
 g=s.boot()
 def cmd(c,timeout=180):
  v=g.cmd(c,timeout=timeout);log.append(c+'\n'+v);return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):cmd(f'dump binary memory tmp/step4/{name}/{label}.bin 0 0x80000')
 cmd('break *0x22c3a');assert 'Breakpoint' in cmd('continue')
 result['first_clock_return']=val('*(unsigned int*)$sp');result['clock_pointer']=val('*(unsigned int*)($sp+4)')
 dump('startup_clock')
 sys.path.insert(0,str(root/'tools'));from overlay_map import decode
 mapping=decode((out/'startup_clock.bin').read_bytes());menu=next(h['base'] for gr in mapping['groups'] if gr['header']==0xf7bc for h in gr['hunks'] if h['number']==160)
 result['ordinary_clock_site']=menu+0x750
 cmd('delete');cmd(f'break *{menu+0x750:#x}');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0');cmd('delete');cmd('break *0x24824');cmd('ignore $bpnum 11');assert 'Breakpoint' in cmd('continue')
 result['warp_after']=cmd('monitor warp-status');assert result['warp_after']=='warp=0'
 dump('anchor');cmd('delete')
 result['capture_reply']=cmd(f'monitor census 600 "" "{out}/window.jsonl"')
 dump('end')
 result['end_pc']=val('$pc')
 result['warp_end']=cmd('monitor warp-status');assert result['warp_end']=='warp=0'
 for f in ('launch.json','fsuae.log'):shutil.copy(root/'amiga/.run'/f,out/f)
 result['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest();result['status']='complete'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'complete',result['end_pc'],flush=True)
except Exception as e:
 result['status']='failed';result['error']=repr(e);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');raise
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
