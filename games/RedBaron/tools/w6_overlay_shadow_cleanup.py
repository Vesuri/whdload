import sys,json,re
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=base+symbol(lines,'overlay_shadow_result')
raw=r.command(f'gdb printf "SHADOW_FREED %u %u %u %u %u %u %u %u\\n", *(unsigned long*){at:#x}, *(unsigned long*){at+4:#x}, *(unsigned long*){at+8:#x}, *(unsigned long*){at+12:#x}, *(unsigned long*){at+16:#x}, *(unsigned long*){at+20:#x}, *(unsigned long*){at+64:#x}, *(unsigned long*){at+68:#x}')
refill=int(re.search(r'CUSTOM4=(\d+)',m['whd_args'])[1])==0x80000
expected='SHADOW_FREED 0 0 0 0 4 4 0 0' if refill else 'SHADOW_FREED 0 0 0 2 2 4 0 0'
assert expected in raw,raw
(p/'shadow-freed.txt').write_text(raw);(p/'capture-shadow.py').write_text(Path('tools/w6_overlay_shadow_capture.py').read_text());print(raw)
