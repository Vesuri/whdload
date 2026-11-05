import os,sys,json,shutil,subprocess
from pathlib import Path
p=Path(sys.argv[1]).resolve();os.environ['RUNTIME_CAPTURE']=str(p)
a=p/'start';a.mkdir()
for n in ('anchor.json','slave.lst','slave.slave','memory.bin'):shutil.copyfile(p/n,a/n)
from runtime_lifecycle_probe import snapshot

from runtime_lifecycle_probe import key,fields,command,m,a,irq,base,s,cap
from profile_window import ROOT
def tap(k):key(k,1);fields(10);key(k,0);fields(10)
tap(0x45);fields(40);tap(0x44);fields(30)
for _ in range(3):tap(0x4d)
tap(0x44);fields(40);tap(0x4d);tap(0x44);fields(100)
x=snapshot('loaded');command('shot '+str(cap/'loaded.png'))

import struct,zlib
packet=(Path(os.environ['GAME'])/'data/a4test.rpl').read_bytes()
assert struct.unpack_from('>HH',packet,8)==(2,9)
assert zlib.crc32(packet[:-4])==int.from_bytes(packet[-4:],'big')
b=(cap/'loaded.bin').read_bytes();i=b.index(b'4DRPLMNU')
version,unused,status,loads,seek,installs,pending=struct.unpack_from('>HH4IH',b,i+8)
assert status==2 and loads==installs==pending==0,(status,loads,installs,pending)
assert x['perf_failure']==x['sim_schedule_overflow']==0
(cap/'abi9-rejection.json').write_text(json.dumps(dict(physics_abi=9,crc_valid=True,load_status=status,loads=loads,installs=installs,pending=pending,message='Replay file missing or invalid.'))+'\n')
