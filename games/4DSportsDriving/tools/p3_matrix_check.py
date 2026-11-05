import subprocess,sys
from pathlib import Path
for name in ('p3_stage_check.py','p3_cache_check.py'):
 subprocess.run([sys.executable,str(Path(__file__).with_name(name)),sys.argv[1]],check=True)
