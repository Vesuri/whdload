import sys,subprocess
from pathlib import Path
import route_status as r
base=sys.argv[1]
for key in sys.argv[2:]:
 code={"return":68,"tab":66,"right":78,"f10":89,"esc":69}[key]
 for edge in ("down","up"):
  subprocess.run([sys.executable,"tools/completion_host_input.py",f"irq-{edge}:{base},200588,{code}"],check=True,stdout=subprocess.DEVNULL)
  r.command("wait 0.15")
 r.command("stop")
 print("IRQ",key,flush=True)
