import json,re,struct,sys
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text());e=m['entry'];listing=(out/'slave.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
base=e['game_anchor']-sym('tape_game_anchor')
raw=r.command(f'gdb delete\nbreak *{base+sym("cpu_span_twin_fail"):#x}\nbreak *{e["game_anchor"]:#x}\nignore $bpnum 7\ncontinue\ninfo registers pc\ndelete')
(out/'native-twin.log').write_text(raw)
assert re.search(rf'Breakpoint \d+, 0x{e["game_anchor"]:x} in',raw),raw
for name,count in [('cpu_span_header',20),('cpu_span_counts',8),('perf_chiprev',4),('perf_mask',4)]:
 at=base+sym(name)
 r.command(f'gdb dump binary memory {out}/{name}.bin {at:#x} {at+count:#x}')
header=(out/'cpu_span_header.bin').read_bytes();assert header[:8]==b'RBSPAN01'
version,twins,words=struct.unpack('>3I',header[8:]);cpu,fallback=struct.unpack('>2I',(out/'cpu_span_counts.bin').read_bytes());chiprev=int.from_bytes((out/'perf_chiprev.bin').read_bytes(),'big');mask=int.from_bytes((out/'perf_mask.bin').read_bytes(),'big')
result=dict(version=version,twins=twins,words=words,cpu=cpu,fallback=fallback,chiprev=chiprev,mask=mask,slave_sha256=m['slave_sha256'])
assert version==1 and twins>0 and cpu>0 and cpu+fallback==twins and mask&(1<<19),result
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
print(r.command('quit'),flush=True)
