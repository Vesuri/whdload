import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import call_costs
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');paths=[p/f'capacity-{i}/trace.bin' for i in range(3)]
def routine(name):
 start=symbol(lines,name);ret=None
 for line in lines:
  x=re.match(r'00:([0-9A-F]+)\s+4E75\s',line)
  if x and int(x[1],16)>=start:ret=int(x[1],16);break
 assert ret is not None
 return base+start,base+ret
routines={n:routine(n) for n in ['time_pose_capture','time_pose_blend','time_render_frame','time_loop_poll','time_core_advance']}
trace=barto.load(paths[0]);pages={regs[15]&~0xfff for field in trace.fields for pc,_,regs in trace.instructions(field) if pc==m['entry']['sim']+0x2ffcc};assert len(pages)==1,pages
low=pages.pop();del trace
result=call_costs.measure(paths,m['entry']['sim'],low,low+4096,routines)
(p/'capacity-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary'],indent=2))
