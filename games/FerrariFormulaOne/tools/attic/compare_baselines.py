#!/usr/bin/env python3
"""Conservative loaded-code and controlled-race equivalence checks."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[1];p=root/'tmp/baseline'
mapping=json.loads((p/'loaded-map.json').read_text())
# Three slave pointers in mapped code and the timing hook. Do not normalize
# arbitrary pointer-looking values: each is an audited slave call operand.
pointers=[0x19a88,0x1b9f4,0x6551a,0x6a306]
def normalized(data):
 b=bytearray(data)
 for off in pointers:
  b[off:off+4]=b'HOOK'
 return b
report={'loaded_code_bytes':sum(x['size'] for x in mapping),'mapped_segments':len(mapping),'normal':{},'controlled':{}}
for custom in (0,1):
 a=(p/f'shipped-c{custom}-valid/race-0.bin').read_bytes();b=(p/f'release-c{custom}-valid/race-0.bin').read_bytes()
 na,nb=normalized(a),normalized(b)
 differences=[]
 for h in mapping:
  lo,hi=h['base'],h['base']+h['size']
  differences += [hex(i) for i in range(lo,hi) if na[i]!=nb[i]]
 assert not differences,differences
 # Check each old SPS bug fix and timing option explicitly outside map coverage.
 assert a[0x6b0ba:0x6b0bc]==b[0x6b0ba:0x6b0bc]==bytes.fromhex('9240')
 assert a[0x65518:0x6551a]==b[0x65518:0x6551a]==bytes.fromhex('4eb9')
 assert a[0x6a304:0x6a306]==b[0x6a304:0x6a306]==(bytes.fromhex('4eb9') if custom==0 else bytes.fromhex('e340'))
 report['normal'][str(custom)]={'normalized_loaded_code_equal':True,'sps_bugfixes_present':True,'timing_gate_correct':True}
for count in (1,10,100):
 a=(p/f'shipped-c0-controlled/race-{count}.bin').read_bytes();b=(p/f'release-c0-controlled/race-{count}.bin').read_bytes()
 na,nb=normalized(a),normalized(b)
 lo,hi=0x64a68,0x6ef20
 assert na[lo:hi]==nb[lo:hi],count
 assert a[0x24f60:0x24fd8]==b[0x24f60:0x24fd8],count
 # Verify nonempty state coverage and fail a deliberate mutation.
 poison=bytearray(nb);poison[0x66c54]^=1
 assert na[lo:hi]!=poison[lo:hi]
 report['controlled'][str(count)]={'race_region_bytes':hi-lo,'equal_after_two_slave_pointer_normalizations':True,'rng_bytes_equal':120,'negative_control_rejected':True}
a=Image.open(p/'shipped-c0-controlled/race.png').convert('RGB');b=Image.open(p/'release-c0-controlled/race.png').convert('RGB')
box=(54,36,694,436)
assert ImageChops.difference(a.crop(box),b.crop(box)).getbbox() is None
report['controlled_game_image']={'crop':box,'pixels':640*400,'equal':True,'whole_capture_difference_bbox':ImageChops.difference(a,b).getbbox()}
(p/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
