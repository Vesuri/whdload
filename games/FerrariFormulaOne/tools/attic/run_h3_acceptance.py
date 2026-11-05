from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
for group in sys.argv[1:]:
 subprocess.run([sys.executable,str(r/'tools/run_h3_checks.py'),group],check=True)
