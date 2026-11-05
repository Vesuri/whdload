import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());e=json.loads((p/'flight-exit.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n)
raw=r.command('gdb printf "RETURN %u %u\\n", $pc, *(unsigned int*)($a5+4)');(p/'exit-return-before.log').write_text(raw);pc,target=map(int,re.search(r'RETURN ([0-9 ]+)',raw)[1].split());assert pc==at('time_loop_exit')
raw=r.command(f'gdb delete\ntbreak *{target:#x}\ncontinue\nprintf "CLEAN %u %u %u %u\\n", $pc, $d0, *(unsigned long*){at("time_loop_state")+40:#x}, *(unsigned short*){at("time_keys_ready"):#x}');(p/'exit-return-after.log').write_text(raw)
values=list(map(int,re.search(r'CLEAN ([0-9 ]+)',raw)[1].split()));assert values==[target,e['return_value'],0,0],values
(p/'exit-cleanup.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],return_preserved=True,active=0,keys_ready=0,started=e['started'],last_captured=e['completed']),indent=2)+'\n');print(values)
