#!/usr/bin/env python3
"""Read-only native frame-latch and mountain-output samples; no input injection."""
import json,re
from harness import ROOT,server,command

def capture(out,source,frames=32):
 out.mkdir(parents=True,exist_ok=False);m=json.loads((source/'capture.json').read_text());b=(source/'code.bin').read_bytes();h=m['regions']['h4'];db=m['regions']['td-data'];a4=db+0x7ffe
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(source/'slave.lst').read_text(encoding='latin1'),re.M)}
 off=m['regions']['td']+0x6390-m['base'];slave=int.from_bytes(b[off+2:off+6],'big')-syms['overlay_unload_end'];st=slave+syms['render_heading_state']
 server.request('until '+hex(h+0xb68))
 lines=[f'break *{h+0xb68:#x}',f'break *{h+0x1ea8:#x}','set $td_s=0',f'while $td_s < {frames*4}',f'if $pc == {h+0xb68:#x}',f'printf "LATCH %u %u %ld %ld %d %d %ld %ld %ld %ld %ld %ld\\n", *(unsigned int*)($a4-31782), *(unsigned int*)($a4-22340), *(int*)($a4-22372), *(int*)($a4-22328), *(short*)($a4-29280), *(short*){st:#x}, *(int*){st+2:#x}, *(int*){st+6:#x}, *(int*)($a4-29278), *(int*)($a4-29274), *(int*)($a4-29270), *(int*)($a4-29266)','else','printf "DRAW %u %u %u\\n", ($d2&65535)/4, $d0&65535, $d1&65535','set $td_s=$td_s+1','end',f'if $td_s < {frames*4}','continue','end','end','delete']
 (out/'gdb.txt').write_text(command('\n'.join(lines)));(out/'metadata.json').write_text(json.dumps(dict(frames=frames,options=m['options']),indent=2)+'\n')
