from pathlib import Path
import shutil
root=Path('tmp/prof/p7-integration')
p=Path('tools/p7_save.py');p.write_text(Path('tools/p5_save.py').read_text().replace('tools/runtime_replay_record.py','tools/runtime_later_checkpoint_record.py'))
p=Path('tools/p7_reload.py');p.write_text(Path('tools/workspace_reload.py').read_text().replace('(200,400,600)','(1500,1550,1600)').replace('>600','>1600').replace('==600','==1600'))
# Retained evidence may be compressed; support reads without temporary expansion.
Path('tools/p7_lifecycle.py').write_text('import p7_offline,runpy\nrunpy.run_path("tools/p5_crash_finish.py",run_name="__main__")\n')
p=Path('tools/replay_file_check.py');p.write_text(p.read_text().replace('(2,9,50,20,1828,22400,7840)','(2,10,50,20,1828,22400,7840)'))
for name,original in [('save-game','tmp/p5-route-replay/game'),('reject-game','tmp/p5-route-replay/game')]:
 dst=root/name;shutil.copytree(original,dst)
 if name=='save-game':
  for p in dst.glob('data/*.rpl'):p.unlink()
 shutil.copyfile('tmp/game/sim-prefs-50/data/4DPhysics.cfg',dst/'data/4DPhysics.cfg')
# Read-only legacy-version load through existing UI, with validation marker proof.
s=Path('tools/workspace_reload.py').read_text();s=s[:s.index("packet=(Path")]+'''
import struct,zlib
packet=(Path(os.environ['GAME'])/'data/a4test.rpl').read_bytes()
assert struct.unpack_from('>HH',packet,8)==(2,9)
assert zlib.crc32(packet[:-4])==int.from_bytes(packet[-4:],'big')
b=(cap/'loaded.bin').read_bytes();i=b.index(b'4DRPLMNU')
version,unused,status,loads,seek,installs,pending=struct.unpack_from('>HH4IH',b,i+8)
assert status==2 and loads==installs==pending==0,(status,loads,installs,pending)
assert x['perf_failure']==x['sim_schedule_overflow']==0
(cap/'abi9-rejection.json').write_text(json.dumps(dict(physics_abi=9,crc_valid=True,load_status=status,loads=loads,installs=installs,pending=pending,message='Replay file missing or invalid.'))+'\\n')
'''
Path('tools/p7_reject.py').write_text(s)
