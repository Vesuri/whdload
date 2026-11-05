from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
p=subprocess.Popen([sys.executable,str(r/'tools/test_release_legacy_live.py'),sys.argv[1] if len(sys.argv)>1 else 'a500'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
 for line in p.stdout:
  print(line.rstrip(),flush=True)
  if 'Modal controls ready' in line:
   replay=subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),str(r/'tools/release-race-control-replay.json')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   (r/'tmp/step5/release-route-replay.log').write_text(replay.stdout)
   if replay.returncode: raise RuntimeError(replay.stdout[-4000:])
   subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),str(r/'tools/release-season-replay.json')],check=True)
   print('Season saved; F10 return awaiting visual verification',flush=True)
 assert p.wait()==0
finally:
 if p.poll() is None:p.terminate();p.wait()
