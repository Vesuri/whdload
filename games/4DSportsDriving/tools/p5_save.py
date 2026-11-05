import os,sys,json,shutil,subprocess
from pathlib import Path
p=Path(sys.argv[1]).resolve();os.environ['RUNTIME_CAPTURE']=str(p)
a=p/'start';a.mkdir()
for n in ('anchor.json','slave.lst','slave.slave','memory.bin'):shutil.copyfile(p/n,a/n)
from runtime_lifecycle_probe import snapshot
s=snapshot('p5-start')
assert s['consumer']<200,s
subprocess.run([sys.executable,'tools/runtime_replay_record.py'],check=True)
subprocess.run([sys.executable,'tools/runtime_later_checkpoint_save.py'],check=True)

from runtime_lifecycle_probe import command,base,s
# The writer counter is published only after CRC/readback; a fixed field wait
# can stop inside the writer even though the host file is already complete.
for ext in ('bin','json'):(p/('saved.'+ext)).rename(p/('save-pending.'+ext))
command(f"gdb delete\ntbreak *{base+s['sim_replay_save_marker']-8:#x}\ncontinue\ndelete")
snapshot('saved')
