from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
p=subprocess.Popen([sys.executable,str(r/'tools/test_h3_manual.py'),sys.argv[1] if len(sys.argv)>1 else 'a500'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
 for line in p.stdout:
  print(line.rstrip(),flush=True)
  if 'Modal controls ready' in line:
   subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),str(r/'tools/drive-select-f1.json')],check=True)
   replay=subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),str(r/'tools/h3-manual-test.json')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   (r/'tmp/step5/release-modal-replay.log').write_text(replay.stdout)
   if replay.returncode:
    subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),'[{"op":"quit"}]'])
    raise RuntimeError(replay.stdout[-4000:])
 assert p.wait()==0
finally:
 if p.poll() is None:p.terminate();p.wait()
