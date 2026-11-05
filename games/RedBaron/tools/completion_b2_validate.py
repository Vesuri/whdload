import os,sys,subprocess,json
from pathlib import Path
sys.path.insert(0,"tools");from completion_machines import environment
sys.path.insert(0,"tools");import route_status as r
for machine in ("020","030-nommu"):
 env=environment(machine,196608);env.update(BOOT_TIMEOUT="240",GAME_DIR='completion-benchmark/RedBaron')
 env["WHD_ARGS"]=env["WHD_ARGS"].replace("CUSTOM5=0","CUSTOM5=8")
 out="tmp/prof/completion-b2-enabled-"+machine
 subprocess.run([sys.executable,"-B","tools/reach_flight.py","--no-shot","--out",out],env=env,check=True)
 subprocess.run([sys.executable,"-B","tools/paint_log.py","--out",out+"/cache.json"],env=env,check=True)
 cache=json.loads(Path(out+"/cache.json").read_text());assert cache["raw_cacr"]&1 and not cache["raw_cacr"]&256,cache
 print(r.command("quit"),flush=True)
for machine,base in (("020",0x11fbf),("030-nommu",0x10fba)):
 for state,mask in (("off",base),("on",base|0x20000)):
  env=dict(os.environ,BENCH_DEVELOPER="1",BENCH_OPENING_ONLY="1")
  out="tmp/prof/completion-b2-"+machine+"-"+state
  subprocess.run([sys.executable,"-B","tools/completion_matrix_case.py",machine,str(mask),out],env=env,check=True)
print("B2 VALIDATION COMPLETE",flush=True)
