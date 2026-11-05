#!/usr/bin/env python3
"""Actual native-menu corrupt replay rejection and continued A4000 driving."""
from pathlib import Path
import json,struct,hashlib,zlib
r=Path('tmp/runtime-badcrc-load');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base'];launch=json.loads((r/'launch.json').read_text())
def load(n):return json.loads((r/(n+'.json')).read_text())
def ptr(b,o):return struct.unpack_from('>I',b,a+o)[0]-m['memory_base']
def sem(b):
 v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for marker,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;v+=b[p:p+n]
 assert len(v)==1510;return v
file=(r/'game/data/badcrc.rpl').read_bytes();original=Path('tmp/runtime-save-nowritecache/a4test.rpl').read_bytes();assert len(file)==len(original)==62108
assert [i for i,(x,y)in enumerate(zip(file,original))if x!=y]==[1864]
assert zlib.crc32(file[:-4])!=int.from_bytes(file[-4:],'big')
assert hashlib.sha256(file).hexdigest()==launch['badfile_sha256']
b=(r/'before-load.bin').read_bytes();state=load('before-load')
for name in ('rejected','notice','returned'):
 c=(r/(name+'.bin')).read_bytes();assert sem(c)==sem(b),name
 assert c[a-0x1750:a-0x1736]==b[a-0x1750:a-0x1736]
 for off,n in [(-0x1778,1802),(-0x1770,30000),(-0x16bc,22400)]:
  p,q=ptr(b,off),ptr(c,off);assert b[p:p+n]==c[q:q+n],(name,off)
 p=b.index(b'4DHISTRY')+28;q=c.index(b'4DHISTRY')+28;assert b[p:p+7840]==c[q:q+7840]
 p=c.index(b'4DRPLMNU');assert struct.unpack_from('>HH4IH',c,p+8)==(1,0,2,0,0xffffffff,0,0)
 s=load(name)
 for k in ('consumer','imported','recorded_length','sim_schedule_ticks','selected','active_rate','recorded_rate','mode','replay_pause'):
  assert s[k]==state[k],(name,k)
 assert s['perf_failure']==s['sim_schedule_overflow']==0
s,t=load('resumed'),load('resumed-250');assert t['sim_clock_fields']-s['sim_clock_fields']==250
assert t['sim_schedule_ticks']-s['sim_schedule_ticks']==250
completed=t['consumer']-s['consumer'];assert completed==248
assert t['sim_schedule_read']-s['sim_schedule_read']==completed
assert t['queue']-s['queue']==250-completed
assert t['active_rate']==t['recorded_rate']==50 and t['mode']==0 and t['perf_failure']==t['sim_schedule_overflow']==0
c=(r/'resumed-250.bin').read_bytes();p=ptr(c,-0x1770);assert not any(c[p+s['consumer']:p+t['consumer']])
assert Path('tmp/run/default/.run/dh1/data/badcrc.rpl').read_bytes()==file
report=dict(runtime_sha256=launch['slave_sha256'],corrupt_file_sha256=launch['badfile_sha256'],corrupt_offset=1864,load_status=2,loads=0,installs=0,pending=0,equal_semantic_bytes=1510,equal_input_bytes=30000,equal_native_checkpoints=22400,equal_companions=7840,equal_prefix_and_track_bytes=1828,notice='Replay file missing or invalid.',continued_window=dict(fields=250,published=250,completed=248,backlog_change=2,controls='all248 resumed samples zero'),guest_memory_modified=False,scope='Native Load Replay selects real CRC-invalid ABI9 file twice. First held Enter dismisses notice; second uses read-only breakpoint at notice entry to release Enter, then renders notice. Rejection preserves all replay/simulation data and native Continue Driving works. WARP1 correctness, not capacity. Other malformed variants, resource changes and cached-save persistence remain separate.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
