#!/usr/bin/env python3
"""Check original hook instructions and direct incoming branches for the audio fix."""
import json,struct
from td_report import game_bytes
b=game_bytes()[40:40+0x7c0c]
hooks={0x2574:'3d400096217cffffffff0016',0x2684:'3d420096216c84c40004',0x26ca:'302e001cc07c0780394084ca3d7c0780009a',0x276a:'302c84ca6708807c80003d40009a4a2c84c967063d6c84c800964cdf130470004e75'}
for h,v in hooks.items():assert b[h:h+len(bytes.fromhex(v))]==bytes.fromhex(v),hex(h)
incoming=[]
for a in range(0,len(b)-6,2):
 w=int.from_bytes(b[a:a+2],'big');t=None
 if w>>12==6:
  d=struct.unpack('b',b[a+1:a+2])[0]
  if not d:d=struct.unpack('>h',b[a+2:a+4])[0]
  t=a+2+d
 elif w&0xf0f8==0x50c8 or w in (0x4eba,0x4efa):t=a+2+struct.unpack('>h',b[a+2:a+4])[0]
 elif w in (0x4eb9,0x4ef9):t=int.from_bytes(b[a+2:a+6],'big')
 for h,v in hooks.items():
  end=h+len(bytes.fromhex(v))
  if t is not None and h<=t<end and not h<=a<end:
   incoming.append([hex(a),hex(t)]);assert t==h,'external branch into replaced range'
print(json.dumps(dict(status='PASS',hooks={hex(k):len(bytes.fromhex(v)) for k,v in hooks.items()},incoming=incoming,limit='Conservative word-aligned direct branch scan; indirect targets are not statically proven.'),indent=2))
