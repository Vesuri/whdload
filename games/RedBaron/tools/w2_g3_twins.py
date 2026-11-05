import json,os,re,struct,subprocess,sys
from pathlib import Path
import route_status as r,step_log
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,default=1);revision=parser.parse_args().revision
suffix='' if revision==1 else f'-r{revision}'
out=Path('tmp/prof/w2-g3-twins-a500'+suffix);assert not out.exists()
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
from os import environ
env=dict(environ,MallocScribble='1',AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS='--slow_memory=1536 --uae_cpu_multiplier=2 --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true',WHD_ARGS='CUSTOM2=16 CUSTOM5=8706');env.pop('BOOT_BREAK',None)
with Path('tmp/w2-g3-twins.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
marker=r.locate();state=r.read(marker);base=marker-label('tape_marker');fail=base+label('vertex_verify_fail')
reply=r.command(f'gdb break *{fail:#x}\nbreak *{state["game_anchor"]:#x}\nignore $bpnum 38\ncontinue\nprintf "G3_STOP %u\\n", $pc\ndelete');(out/'run.txt').write_text(reply)
end=step_log.collect();(out/'steps.json').write_text(json.dumps(end,indent=2)+'\n')
marker=r.locate();b=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();(out/'checks-memory.bin').write_bytes(b)
index=base+label('vertex_verify_header')-r.DUMP_BASE;v,total,synthetic=struct.unpack_from('>3I',b,index+8)
result=dict(version=v,total=total,synthetic=synthetic,step=end['count'],passed=f'G3_STOP {state["game_anchor"]}' in reply and end['count']==40 and synthetic==208 and total>synthetic)
(out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
assert result['passed'],reply
print(r.command('shot '+str((out/'bank.png').resolve())),flush=True)
