from pathlib import Path
import time,json,subprocess,sys
r=Path(__file__).resolve().parents[1]
while True:
 p=r/'manifest/render-h6-baseline.json'
 if p.exists() and json.loads(p.read_text())['status']=='passed':break
 time.sleep(10)
print('H6 finished; begin baseline lifecycle/enabler audit',flush=True)
subprocess.run([sys.executable,str(r/'tools/run_h7_lifecycle.py'),'baseline'],check=True)
