"""One bounded integration check; not a pixel twin or performance result."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,'tools')
import route_status as r
out=Path('tmp/prof/completion-e2-cockpit-stage')
entry=json.loads((out/'entry.json').read_text())['entry']
sym={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
base=entry['game_anchor']-sym['tape_game_anchor'];sim=entry['sim']
def at(n):return base+sym[n]
raw=r.command(f'gdb delete\nbreak *{sim+0x3154a:#x}\nignore $bpnum 9\ncontinue\ndelete')
assert re.search(rf'Breakpoint \d+, 0x{sim+0x3154a:x} in',raw),raw
(out/'publications.log').write_text(raw)
commands=[f'printf "STAGE %u %u %u %u %u\\n", *(unsigned int*){at("cockpit_stage_counts"):#x}, *(unsigned int*){at("cockpit_stage_counts")+4:#x}, *(unsigned int*){at("cockpit_stage_pool"):#x}, *(unsigned int*){at("cockpit_stage_active"):#x}, *(unsigned int*){at("cockpit_stage_h3"):#x}']
raw=r.command('gdb '+'\n'.join(commands));(out/'stage.log').write_text(raw)
begins,ends,pool,active,h3=map(int,re.search(r'STAGE ([0-9 ]+)',raw)[1].split())
assert begins==ends and begins>=10 and 0<pool<2*1024*1024 and active==0,raw
raw=r.command(f'gdb printf "TARGETS %u %u\\n", *(unsigned int*){h3+0x9d6a:#x}, *(unsigned int*){h3+0x9d72:#x}')
targets=list(map(int,re.search(r'TARGETS ([0-9 ]+)',raw)[1].split()))
assert all(not pool<=a<pool+80000 for a in targets),raw
result=dict(entries=begins,exits=ends,chip_pool=pool,active=active,targets=targets,scope='Ten publication integration check; no pixel twin or FPS claim')
(out/'stage-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
print(r.command('shot '+str((out/'front.png').resolve())),flush=True)
