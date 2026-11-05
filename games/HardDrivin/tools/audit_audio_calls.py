import json,sys,struct
from pathlib import Path
from game_image import ROOT,hunks
h=hunks();code=h[0]['data'];data=h[1]['data'];callers=[i for i in range(0,0x11a4e,2) if code[i:i+4]==bytes.fromhex('4eac8032')]
classified={0x6b94:5,0x7d8e:10,0x851a:1,0x8e4c:3,0x92f6:3,0x93b4:2,0x93f4:2,0xb166:8,0xb624:4,0xbc18:9,0xbcf6:6,0xbd02:7,0xbdd6:6,0xbde2:7,0xc004:6,0xcc4e:6,0xcc84:7,0xcd52:7,0x10c24:4,0x10e10:6,0x11486:0}
assert callers==sorted(classified)
for off,arg in classified.items():
 if arg:assert code[off-4:off]==struct.pack('>HH',0x3f3c,arg)
 else:assert code[off-2:off]==bytes.fromhex('4267')
assert struct.unpack_from('>I',data,0x32)[0]==0x8ae
r=dict(passed=True,direct_vector_callers=[dict(offset=hex(i),event=classified[i]) for i in callers],scope='All aligned direct JSR through the original sound-event vector in the native engine extent; indirect runtime calls are not proven absent by this scan.')
(ROOT/'tmp/analysis/audio-call-audit.json').write_text(json.dumps(r,indent=2)+'\n');print('Native sound-event call inventory PASS:',len(callers))
