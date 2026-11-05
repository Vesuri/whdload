import json,re,struct,sys
from pathlib import Path
import route_status as r
root=Path(__file__).resolve().parents[1]
name=sys.argv[1];out=root/'tmp/prof'/name
base=json.loads((out/'diagnostic-base.json').read_text())['base']
symbols=(out/'slave.lst').read_text(encoding='latin1')
sym=int(re.search(r'^fast_frame_verify_header\s+00:([0-9a-fA-F]+)',symbols,re.M)[1],16)
print(r.command(f'gdb dump binary memory tmp/prof/{name}/header.bin {base+sym:#x} {base+sym+120:#x}'))
b=(out/'header.bin').read_bytes();v=struct.unpack('>28I',b[8:]);print(b[:8],v)
expected=int(sys.argv[2])
assert v[3]==expected,(v[3],expected)
if expected!=0xffffffff:assert v[4]!=v[5]
(out/'result.json').write_text(json.dumps(dict(version=v[0],blits=v[1],words=v[2],difference=v[3],cpu=v[4],native=v[5],slot=v[6],counts=v[7:]),indent=2)+'\n')
print(r.command('quit'))
