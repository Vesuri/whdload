import os,sys,subprocess,json
from pathlib import Path
sys.path.insert(0,"tools");from completion_machines import environment
sys.path.insert(0,"tools");import route_status as r,step_log
for machine in ("030","030-nommu","040","060"):
 env=environment(machine,65536);env.update(BOOT_TIMEOUT="240",GAME_DIR='completion-benchmark/RedBaron')
 env["WHD_ARGS"]=env["WHD_ARGS"].replace("CUSTOM5=0","CUSTOM5=8")
 out="tmp/prof/completion-b2-cache-"+machine
 subprocess.run([sys.executable,"-B","tools/reach_flight.py","--no-shot","--out",out],env=env,check=True)
 subprocess.run([sys.executable,"-B","tools/paint_log.py","--out",out+"/cache.json"],env=env,check=True)
 print(machine,Path(out+"/cache.json").read_text(),flush=True)
 print(r.command("quit"),flush=True)
