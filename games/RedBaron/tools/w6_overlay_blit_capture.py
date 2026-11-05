"""Observe private compositor self-tests before their buffers are freed."""
import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);header=at('overlay_blit_result');cases=[]
r.command(f'gdb delete\nbreak *{at("overlay_blit_test_observed"):#x}\nbreak *{at("overlay_blit_bad"):#x}')
for case in (1,2):
 r.command('gdb continue')
 raw=r.command(f'gdb printf "BLIT %u %u %u %u %u %u\\n", $pc, *(unsigned long*){header:#x}, *(unsigned long*){header+4:#x}, *(unsigned long*){header+8:#x}, *(unsigned long*){header+12:#x}, *(unsigned short*)0xdff002')
 match=re.search(r'BLIT (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',raw);assert match,raw
 pc,chip,cpu,count,checked,dmacon=map(int,match.groups());assert pc==at('overlay_blit_test_observed') and count==case and checked==case*45240 and not dmacon&0x4000
 for name,ptr,size in [('chip',chip,45240),('cpu',cpu,40000)]:r.command(f'gdb dump binary memory {p}/blit-{case}-{name}.bin {ptr:#x} {ptr+size:#x}')
 cases.append(dict(case=case,count=count,checked=checked,dmacon=dmacon));(p/'blit-capture.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],cases=cases),indent=2)+'\n');print(case,checked,flush=True)
r.command(f'gdb delete\nbreak *{m["entry"]["game_anchor"]:#x}\ncontinue\ndelete')
raw=r.command(f'gdb printf "FREED %u %u %u %u\\n", *(unsigned long*){header:#x}, *(unsigned long*){header+4:#x}, *(unsigned long*){header+8:#x}, *(unsigned long*){header+12:#x}')
assert 'FREED 0 0 2 90480' in raw,raw
(p/'blit-freed.txt').write_text(raw)
