#!/usr/bin/env python3
"""Independently check the live exact-score codec and optional saved sidecar."""
import argparse
import json
from pathlib import Path
import re
import struct
import zlib

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--saved',type=Path)
a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes()
symbols={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
markers={}
for tag,expected in ((b'4DSCORE!',(1,89,89)),(b'4DSCFILE',(1,470,470))):
 starts=[m.start() for m in re.finditer(re.escape(tag),b) if struct.unpack_from('>HHI',b,m.start()+8)==expected]
 assert len(starts)==1,(tag,starts)
 markers[tag.decode()]={'offset':starts[0],'version':expected[0],'count':expected[1],'passed':expected[2]}
base=markers['4DSCFILE']['offset']+12-symbols['sim_score_file_passed']
if 'sim_score_io_passed' in symbols:
 at=base+symbols['sim_score_io_passed']
 assert b[at-12:at-4]==b'4DSCIO!!'
 assert struct.unpack_from('>HHI',b,at-4)==(1,8,8)
 markers['4DSCIO!!']={'version':1,'count':8,'passed':8}
guards={'sim_score_test_native_guard':0x11223344,'sim_score_test_native_end':0x55667788,
        'sim_score_test_file_guard':0x12345678,'sim_score_test_file_end':0x87654321,
        'sim_score_test_out_guard':0x13572468,'sim_score_test_out_end':0x24681357,
        'sim_score_file_guard_before':0x53434f52,'sim_score_file_guard_after':0x45475541,
        'sim_score_file_readback_guard':0x52442121}
for name,value in guards.items():
 assert struct.unpack_from('>I',b,base+symbols[name])[0]==value,name
exact=[0,2,5,150000,327670,0x1fffffffe,0xffffffffffffffff]
native=bytearray(i&255 for i in range(364))
for i,value in enumerate(exact):
 struct.pack_into('>H',native,i*52+50,(value+4)//5 if value<=327670 else 65535)
body=bytes(native)+struct.pack('>7Q',*exact)
expected=struct.pack('>8sHHII',b'4DHIG100',1,7,364,zlib.crc32(body))+body
assert len(expected)==440
at=base+symbols['sim_score_test_file']
assert b[at:at+440]==expected,'68000 encoder differs from Python struct/zlib oracle'
if a.saved:
 assert a.saved.read_bytes()==expected,'disk file differs from independently encoded golden bytes'
 (a.capture/'saved-sidecar.hix').write_bytes(a.saved.read_bytes())
result={'markers':markers,'guard_count':len(guards),'sidecar_size':len(expected),'crc32':hex(zlib.crc32(body)),
        'exact_hundredths':exact,'saved_file_verified':bool(a.saved)}
(a.capture/'score-file-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
