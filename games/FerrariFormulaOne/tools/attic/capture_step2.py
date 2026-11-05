#!/usr/bin/env python3
from pathlib import Path
import os,sys,re,json,signal,shutil,time,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];variant=sys.argv[2] if len(sys.argv)>2 else 'probe-s0-p1-w0';out=root/'tmp/step2'/name;out.mkdir(parents=True,exist_ok=True)
listing=(root/f'tmp/build/step2/{variant}.list').read_text();symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)',listing,re.M)}
os.environ.update(SLAVE=str(root/f'tmp/build/step2/{variant}.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=0',DETERMINISTIC='1')
s=Server('ff1probe',root=str(root),profile_window=False);log=[];result={}
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def until(addr):
  cmd('delete');cmd(f'break *{addr:#x}');v=cmd('continue');assert 'Breakpoint' in v,v
 def dump(label):cmd(f'dump binary memory tmp/step2/{name}/{label}.bin 0 0x80000')
 until(0x19a86)
 stub=val('*(unsigned int*)0x19a88')-0x14d4+5440
 symbols={k:v+stub for k,v in symbols.items()};result['symbols']=symbols
 until(symbols['profile_ready']);assert val(f'*(unsigned int*){symbols["error"]}')==0
 dump('profile-ready');cmd(f'dump binary memory tmp/step2/{name}/saved-profile.bin {symbols["profile_state"]} {symbols["profile_state"]+46}')
 print(name,'profile ready, warp result',val(f'*(unsigned int*){symbols["warp_result"]}'),flush=True)
 result['qOffsets']=cmd('maintenance packet qOffsets');assert '00001018' in result['qOffsets'],result
 until(symbols['profile_restored']);dump('profile-restored')
 b=(out/'profile-restored.bin').read_bytes();saved=(out/'saved-profile.bin').read_bytes();task=struct.unpack_from('>I',saved,2)[0]
 assert b[0x1000:0x1020]==saved[14:46]
 assert b[task+128:task+132]==saved[6:10] and b[task+140:task+144]==saved[10:14]
 result['profile_metadata_restored']=True
 result['warp_before']=cmd('monitor warp-status');assert 'warp=1' in result['warp_before']
 cmd('monitor warp 0')
 result['warp_switch_fields']=val(f'*(unsigned int*){symbols["fields"]}')
 # next completed simulation after the profiling IRQ; warp transition has settled
 until(symbols['simulation_done']);cmd('ignore $bpnum 3');cmd('continue');dump('anchor');result['warp_after']=cmd('monitor warp-status');assert 'warp=0' in result['warp_after']
 result['before']={k:val(f'*(unsigned int*){symbols[k]}') for k in ('updates','renders','publications','geometry_calls','fields','sim_sp','irq_sp','warp_sent','warp_result')}
 cmd('delete');start=time.monotonic();cmd(f'monitor profile 32 "" "{out}/display.bin"');result['capture_wall_seconds']=time.monotonic()-start
 (out/'display.pc-base').write_text('0x1018\n');dump('after-display')
 result['after']={k:val(f'*(unsigned int*){symbols[k]}') for k in ('updates','renders','publications','geometry_calls','fields')}
 shutil.copy(root/f'tmp/build/step2/{variant}.slave',out/'verify.slave');shutil.copy(root/f'tmp/build/step2/{variant}.s',out/'verify.s');shutil.copy(root/'amiga/.run/launch.json',out/'launch.json');shutil.copy(root/'amiga/.run/fsuae.log',out/'fsuae.log')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result['before'],result['after'],result['capture_wall_seconds'],flush=True)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:
  s.g.p.kill()
  try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except ProcessLookupError:pass
