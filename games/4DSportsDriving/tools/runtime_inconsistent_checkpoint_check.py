#!/usr/bin/env python3
"""Before/after native loader regression for an absent checkpoint companion."""
import json,struct,zlib,hashlib
from pathlib import Path
old=Path('tmp/runtime-inconsistent-checkpoint');new=Path('tmp/runtime-inconsistent-fixed');original=Path('tmp/runtime-later-checkpoint/a4test.rpl').read_bytes();file=(old/'game/data/a4test.rpl').read_bytes();expected=bytearray(original);expected[54656:55048]=bytes(392);expected[-4:]=zlib.crc32(expected[:-4]).to_bytes(4,'big');assert file==expected==(new/'game/data/a4test.rpl').read_bytes()
assert 'TARGET 1651' in (old/'seek.log').read_text() and 'HISTORY_FAILURE 1' in (old/'seek.log').read_text()
assert json.loads((old/'loaded.json').read_text())['recorded_length']==1651
m=json.loads((new/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base'];b=(new/'before-load.bin').read_bytes();c=(new/'rejected.bin').read_bytes()
def ptr(v,o):return struct.unpack_from('>I',v,a+o)[0]-m['memory_base']
def sem(v):
 s=v[a-0xa80:a-0x620]+v[a+0x228:a+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=v.index(tag)+12;s+=v[p:p+n]
 assert len(s)==1510;return s
assert sem(b)==sem(c)
assert b[a-0x1750:a-0x1736]==c[a-0x1750:a-0x1736]
for off,n in [(-0x1778,1802),(-0x1770,30000),(-0x16bc,22400)]:assert b[ptr(b,off):ptr(b,off)+n]==c[ptr(c,off):ptr(c,off)+n]
p=b.index(b'4DHISTRY')+28;q=c.index(b'4DHISTRY')+28;assert b[p:p+7840]==c[q:q+7840]
p=c.index(b'4DRPLMNU');assert struct.unpack_from('>HH4IH',c,p+8)==(1,0,2,0,0xffffffff,0,0)
report=dict(file_sha256=hashlib.sha256(file).hexdigest(),old_runtime_reached_history_failure=True,stopped_before_fatal_instruction=True,fixed_runtime_sha256=hashlib.sha256((new/'start/slave.slave').read_bytes()).hexdigest(),fixed_load_status=2,loads=0,installs=0,equal_semantic_bytes=1510,all_replay_buffers_unchanged=True,guest_memory_modified=False)
(new/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
