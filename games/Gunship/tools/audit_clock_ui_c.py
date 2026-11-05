"""Audit actual field duration and retained tick count before result UI."""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1]
l=(root/'tmp/build/clock-ui.slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
for d in map(Path,sys.argv[1:]):
 r=json.loads((d/'clock-ui-result.json').read_text());a=(d/'minute-arena.bin').read_bytes();initial=(d/'active-epoch-arena.bin').read_bytes();ended=(d/'ended-arena.bin').read_bytes()
 def get(data,name,off=0,size=4):return int.from_bytes(data[sym(name)+off:sym(name)+off+size],'big')
 rate=get(a,'RT_CLOCK',22,2);assert rate in (50,60)
 assert get(a,'RT_CLOCK',8)==r['measured_ticks']==192
 assert get(a,'RT_CLOCK',4)==192*rate//3 and get(a,'RT_CLOCK',20,2)==0
 assert get(a,'RT_CLOCK',16)==get(initial,'RT_CLOCK',16)
 for name,off in [('RT_CLOCK',12),('RT_HISTORY',12),('RT_COMMANDS',16),('RT_COMMANDS',20)]:assert get(a,name,off)==0
 assert get(ended,'RT_CAPTURE_OWNER',0,2)==0
 actual_fields=r['measured_field']-r['active_start'];lag=actual_fields-get(a,'RT_CLOCK',4)
 r.update(rate=rate,actual_active_fields=actual_fields,actual_active_seconds=actual_fields/rate,completion_lag_fields=lag,measured_world_rate=192*rate/actual_fields,unexpected_rebases=0,active_time_input_loss=0,ui_expected=f"{r['expected_minutes']:02d}:{r['expected_seconds']:02d}",screenshot_verification='requires visual inspection')
 assert 0<=lag<=10
 (d/'clock-ui-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
