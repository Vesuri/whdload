"""Bounded W5 field-counter and flight-publication probe."""
import json,re,subprocess,sys
from pathlib import Path
import route_status as r,step_log
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text())
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n): return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
base=m['entry']['game_anchor']-label('tape_game_anchor')
print(r.command(f'gdb x/5wx {base+label("pace_state"):#x}'),flush=True)
subprocess.run([sys.executable,'tools/w2_window.py','--out',str(out/'probe-census'),'--step-limit','45','--timeout','55'],check=True)
s=step_log.collect();(out/'probe-steps.json').write_text(json.dumps(s,indent=2)+'\n')
reply=r.command(f'gdb x/5wx {base+label("pace_state"):#x}')
(out/'pace-state.txt').write_text(reply);print(reply)
print('Step interval fields', [b['vbl']-a['vbl'] for a,b in zip(s['records'][1:],s['records'][2:])])
