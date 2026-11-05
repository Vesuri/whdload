import json,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines()
at=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor')+symbol(lines,'overlay_mask_guard_result')
raw=r.command(f'gdb printf "MASK_GUARDS %u %u\\n", *(unsigned long*){at:#x}, *(unsigned long*){at+4:#x}')
assert 'MASK_GUARDS 0 14' in raw,raw
(p/'mask-guards.txt').write_text(raw)
(p/'capture-mask-guards.py').write_text(Path(__file__).read_text())
print(raw)
