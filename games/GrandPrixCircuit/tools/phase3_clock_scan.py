#!/usr/bin/env python3
"""Locate clock-related absolute addresses/strings in every pristine file.
This is a candidate scan, not proof that an embedded constant executes.
"""
from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1]/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit'
a={'VPOSR':0xdff004,'VHPOSR':0xdff006,'CUSTOM_BASE':0xdff000,'CIAA_BASE':0xbfe001,'CIAB_BASE':0xbfd000}
for chip,base in [('CIAA',0xbfe001),('CIAB',0xbfd000)]:
 for name,reg in [('TALO',4),('TAHI',5),('TBLO',6),('TBHI',7),('TODLO',8),('TODMID',9),('TODHI',10),('ICR',13),('CRA',14),('CRB',15)]:a[chip+'_'+name]=base+reg*256
out={}
for p in sorted(r.rglob('*')):
 if not p.is_file():continue
 d=p.read_bytes();hits={}
 for name,n in a.items():
  token=struct.pack('>I',n);at=-1;xs=[]
  while (at:=d.find(token,at+1))>=0:xs.append(hex(at))
  if xs:hits[name]=xs
 for token in [b'timer.device',b'ciaa.resource',b'ciab.resource']:
  if token in d:hits[token.decode()]=hex(d.index(token))
 if hits:out[str(p.relative_to(r))]=hits
print(json.dumps(out,indent=2))
