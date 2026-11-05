"""One boot per machine/scene: all implemented W2 twins, no W1 work."""
import argparse,json,os,re,struct,subprocess,sys
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--scene',choices=['bank','dense'],default='bank');a=p.parse_args()
out=Path(f'tmp/prof/w2-combined-twins-{a.machine}-{a.scene}');assert not out.exists()
common=' --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true'
# bit 4 selects the squadron menu route; bit 2 selects the dense native tape.
custom5=15360+512+(2 if a.scene=='bank' else 20)+(8 if a.machine=='030' else 0)
env=dict(os.environ,MallocScribble='1',WHD_ARGS=f'CUSTOM2=60 CUSTOM5={custom5}');env.pop('BOOT_BREAK',None)
if a.machine=='a500':env.update(AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS='--slow_memory=1536 --uae_cpu_multiplier=2'+common)
elif a.machine=='020':env.update(AMIGA_MODEL='A1200',KICKSTART=os.environ['KICKSTART_A1200'],CPU='68EC020',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=4'+common)
else:env.update(AMIGA_MODEL='A500',CPU='68030',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_data_cache=true'+common,WHD_ARGS=env['WHD_ARGS']+' MMU')
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w2-combined-twins-{a.machine}-{a.scene}.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
marker=r.locate();state=r.read(marker);base=marker-label('tape_marker')
names={'projection':451,'dot':552,'clip':105,'vertex':208}
commands=[f'break *{base+label(n+"_verify_fail"):#x}' for n in names]
commands += [f'break *{state["game_anchor"]:#x}','ignore $bpnum 38','continue','printf "W2_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(commands));(out/'run.txt').write_text(reply)
end=step_log.collect();(out/'steps.json').write_text(json.dumps(end,indent=2)+'\n');r.locate();b=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();(out/'checks-memory.bin').write_bytes(b)
checks={}
for name,expected in names.items():
 v,total,synthetic=struct.unpack_from('>3I',b,base+label(name+'_verify_header')-r.DUMP_BASE+8)
 checks[name]=dict(version=v,total=total,synthetic=synthetic,passed=v==1 and synthetic==expected and total>synthetic)
result=dict(step=end['count'],checks=checks,passed=f'W2_STOP {state["game_anchor"]}' in reply and end['count']==40 and all(x['passed'] for x in checks.values()))
(out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(a.machine,a.scene,result,flush=True);assert result['passed'],reply
if a.machine=='030':
 subprocess.run([sys.executable,'tools/paint_log.py','--out',str(out/'paint.json')],check=True)
 paint=json.loads((out/'paint.json').read_text());assert paint['cacr_valid'] and paint['raw_cacr']==0x2111
print(r.command('shot '+str((out/'step40.png').resolve())),flush=True)
