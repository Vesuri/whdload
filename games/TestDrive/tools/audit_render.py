#!/usr/bin/env python3
"""Audit patch boundaries and extra original tails bypassed by renderer helpers."""
import json,struct
from audit_simulation import ranges,originals,validate

def check():
 rs=ranges();bs=originals();incoming=validate(rs,bs);b=bs['h4'];tails=[]
 from amitools.binfmt.hunk.HunkReader import HunkReader
 from harness import ROOT
 h=HunkReader();assert h.read_file(str(ROOT/'tmp/game/TestDrive_v1.3_0089/TestDrive/data/TD'))==0
 data=next(x['data'] for x in h.hunks if x['type_name']=='HUNK_DATA')
 expected=bytes([0,0,1,1,2,2,3,5,8,10,15,20,25,30,35]+[40]*25)
 assert data[0xb38:0xb60]==expected,'native crest-limit table changed' 
 for start,end in [(0x1184,0x11a0),(0x14ce,0x14ea)]:
  external=[]
  for p in range(0,len(b)-6,2):
   w=int.from_bytes(b[p:p+2],'big');t=None
   if w>>12==6:
    d=struct.unpack('b',b[p+1:p+2])[0]
    if not d:d=struct.unpack('>h',b[p+2:p+4])[0]
    t=p+2+d
   elif w&0xf0f8==0x50c8 or w in (0x4eba,0x4efa):t=p+2+struct.unpack('>h',b[p+2:p+4])[0]
   elif w in (0x4eb9,0x4ef9):t=int.from_bytes(b[p+2:p+6],'big')
   if t is not None and start<=t<end and not start<=p<end:external.append([p,t])
  assert not external,(start,end,external)
  tails.append(dict(start=start,end=end,external_direct_candidates=external))
 return dict(status='PASS',declared_ranges=len(rs),incoming=incoming,bypassed_tails=tails,scope='Word-aligned direct candidates; indirect targets not proven')
if __name__=='__main__':print(json.dumps(check(),indent=2))
