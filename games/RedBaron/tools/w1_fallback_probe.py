"""Break before Abort on a failing lifecycle regression, or at the next flight step."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--flags',type=int,required=True);p.add_argument('--expect',choices=['fail','pass'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
meta=json.loads(Path('tmp/prof/w1-controlled-a500-0/entry.json').read_text())
env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS=meta['extra_args'],WHD_ARGS='CUSTOM2=3 CUSTOM5=864',VERIFY_CACHE_PROBE_FLAGS=str(a.flags),VERIFY_CACHE_PROBE_RESULT=str(a.flags&3))
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/{a.out.name}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(a.out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
listing=(a.out/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
at=r.locate();state=r.read(at);slave=at-label('tape_marker');fail=slave+label('mirror_verify_fail')
reply=r.command(f'gdb break *{fail:#x}\nbreak *{state["game_anchor"]:#x}\ncontinue\nprintf "RB_PROBE %u\\n", $pc\nx/8wx $sp\ndelete');(a.out/'stop.txt').write_text(reply)
match=re.search(r'RB_PROBE (\d+)',reply);assert match,reply
failed=int(match[1])==fail
subprocess.run([sys.executable,'tools/cache_status.py','--entry',str(a.out),'--out',str(a.out/'cache-status.json')],check=True)
(a.out/'checks-memory.bin').write_bytes((r.ROOT/'tmp/build/route-ram.bin').read_bytes())
status=json.loads((a.out/'cache-status.json').read_text());result={'flags':a.flags,'expected':a.expect,'failed_at_verifier':failed,'cache':status['cache'],'checks':status['checks'],'route':status['route']};(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
assert failed==(a.expect=='fail'),result
if not failed:assert status['checks']['lifecycle']==1 and status['route']['game_steps']==2
