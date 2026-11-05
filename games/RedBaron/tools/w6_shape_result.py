import json,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
from shape_lease import check_selftest
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor')
parts=[]
for name,size in [('time_present_shape_cases',24),('time_present_shape_test',16),('time_present_shape_result',4)]:
 addr=base+symbol(lines,name);out=p/(name+'.bin')
 raw=r.command(f'gdb dump binary memory {out} {addr:#x} {addr+size:#x}')
 (p/(name+'.log')).write_text(raw);parts.append(out.read_bytes())
result=check_selftest(*parts);result['sha256']=m['slave_sha256'];result['scope']='Native private-storage copy/restore self-test, not natural changed-selection coverage'
(p/'shape-selftest.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
