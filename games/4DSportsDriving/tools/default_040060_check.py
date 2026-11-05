import subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);subprocess.run([sys.executable,'tools/p5_defaults_check.py',str(p)],check=True);subprocess.run([sys.executable,'tools/p3_cache_check.py',str(p)],check=True)
for n in ['discovery.bin','live-discovery.bin']:(p/n).unlink(missing_ok=True)
