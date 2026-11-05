#!/usr/bin/env python3
"""Read completed physics bodies through a natural bridge jump; no guest writes."""
import json,re,sys,struct,hashlib
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]).resolve();meta=json.loads((p/'anchor.json').read_text());hz=meta['active_simulation_word'];end=int(sys.argv[2])*hz;g=meta['game_base'];first=meta['simulation_tick']+1
assert first<=end
fields=[('tick','unsigned short',-0x940),('x','int',-0x92e),('y','int',-0x92a),('z','int',-0x926),('heading','short',-0x916),('pitch','short',-0x914),('roll','short',-0x912),('speed','unsigned short',-0x904),('slip','short',-0x8f8),('spin','short',-0x8f0),('contact','unsigned char',-0x86d),('w0','unsigned char',-0x86c),('w1','unsigned char',-0x86b),('w2','unsigned char',-0x86a),('w3','unsigned char',-0x869),('crash','unsigned char',-0x865)]
expr=', '.join(f'*({typ} *)($a4+({off}))' for _,typ,off in fields)
fmt=' '.join('%d' for _ in fields)
script=f'''gdb delete
break *{g+0xe7b4:#x}
commands
silent
printf "BODY {fmt}\\n", {expr}
if *(unsigned short *)($a4-0x940)<{end}
continue
end
end
continue
delete
'''
if '--analyze-existing' in sys.argv: out=(p/'bridge.txt').read_text()
else:
 (p/'bridge.gdb').write_text(script);out=command(script);(p/'bridge.txt').write_text(out)
rows=[dict(zip([f[0] for f in fields],map(int,s.split()))) for s in re.findall(r'^BODY (.*)$',out,re.M)]
assert [r['tick'] for r in rows]==list(range(first,end+1)),(len(rows),first,end)
command(f'gdb dump binary memory {p.relative_to(ROOT)}/bridge-end.bin {meta["memory_base"]:#x} {meta["memory_base"]+meta["memory_size"]:#x}')
mem=(p/'bridge-end.bin').read_bytes();a4=meta['data_base']+0x7ffe-meta['memory_base'];history=struct.unpack_from('>I',mem,a4-0x1770)[0]-meta['memory_base'];assert mem[history:history+end]==bytes([1])*end,'Not throttle-only'
result=dict(rate=hz,first=first,end=end,rows=rows,slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),scope='Native completed-body checkpoint, ordinary throttle from stock grid on bridge fixture; no injected pose.')
(p/'bridge.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(rate=hz,first=first,end=end,final=rows[-1],airborne_ticks=[r['tick'] for r in rows if not any(r[f'w{i}'] for i in range(4))],crash_ticks=[r['tick'] for r in rows if r['crash']]),indent=2))
