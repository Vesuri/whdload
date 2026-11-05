import json,re,sys
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);state=json.loads((out/'entry.json').read_text())['entry']
listing=(out/'slave.lst').read_text(encoding='latin1')
def sym(name):
    m=re.search(r'^'+re.escape(name)+r'\s+00:([0-9A-F]+)',listing,re.M)
    if not m:raise ValueError(name)
    return int(m[1],16)
base=state['game_anchor']-sym('tape_game_anchor')
raw=r.command(f'gdb delete\nbreak *{state["sim"]+0x3154a:#x}\nignore $bpnum 4\ncontinue\ndelete')
(out/'publications.log').write_text(raw);print(raw,flush=True)
assert re.search(rf'Breakpoint \d+, 0x{state["sim"]+0x3154a:x} in',raw),raw
cmds=[]
for name,n,kind in [('cockpit_final_counts',5,'unsigned int'),('cockpit_gauge_counts',2,'unsigned int'),('cockpit_gauge_seen_bits',1,'unsigned short'),('cockpit_stage_counts',2,'unsigned int'),('cockpit_static_layer',2,'unsigned int'),('cockpit_foreground_layer',2,'unsigned int'),('cockpit_gauge_pool',1,'unsigned int'),('cockpit_final_pool',1,'unsigned int'),('overlay_solid_entry',1,'unsigned int')]:
    addr=base+sym(name);size=2 if kind=='unsigned short' else 4
    expr=', '.join(f'*({kind}*){addr+i*size:#x}' for i in range(n))
    cmds.append(f'printf "{name} '+(' %u'*n)+f'\\n", {expr}')
raw=r.command('gdb '+'\n'.join(cmds));(out/'layers.log').write_text(raw);print(raw,flush=True)
