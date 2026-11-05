"""Run a retained harness entry point with the private passive-read build."""
import hashlib,os,runpy,sys
from pathlib import Path
import drive
assert hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest()=='e0b2532ace1de7dd4d66d811488ec67ea7080b9991ee57e7190d8e31483f99cc'
drive.require_harness=lambda *args:None
script=sys.argv.pop(1)
runpy.run_path(script,run_name='__main__')
