from pathlib import Path
import os,json,subprocess,sys
r=Path(__file__).resolve().parents[1];profile=json.loads((r/'manifest/step3-profiles.json').read_text())['a1200']
e=dict(os.environ,**profile,WHD_ARGS='CUSTOM1=1',KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(r/'tmp/build/step5-math-v6/logic.slave'),FIELDS='100',OBSERVE='survey',FULL_TRACE='1')
subprocess.run([sys.executable,str(r/'tools/capture_step5_detail.py'),'optimized-detail-v6'],env=e,check=True,timeout=280)
