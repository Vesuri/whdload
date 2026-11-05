from pathlib import Path
import subprocess,sys,os
r=Path(__file__).resolve().parents[1]
# Retain complete filtered boot-to-re-entry logging for020 after correcting
# the logger's output path. Existing first-run lifecycle checks already passed.
subprocess.run([sys.executable,str(r/'tools/run_h7_lifecycle.py'),'baseline'],env=dict(os.environ,H7_LIVE_PROFILES='a1200-fast'),check=True)
subprocess.run([sys.executable,str(r/'tools/run_h7_ownership.py')],check=True)
subprocess.run([sys.executable,str(r/'tools/run_h7_checks.py'),'smoke'],check=True)
