import os,subprocess,sys,json
from pathlib import Path
base=Path.cwd()/'tmp'
flags='-DVERIFY_C_STEP -DVERIFY_C_STEERING -DVERIFY_C_OBJECT_FAST -DVERIFY_C_CACHE -DVERIFY_C_EVENTS -DVERIFY_C_SEED_RNG -DVERIFY_C_POSE_PREDICT -DPOSE_PREDICT_MEASURED -DVERIFY_C_PHYSICS_FAST -DVERIFY_C_PHYSICS_AUX -DVERIFY_C_FAST_STACK -DVERIFY_C_COLLISION_GEOMETRY -DVERIFY_C_LANE_SCAN -DVERIFY_C_FUSED_LEAN -DSTEP_CAPTURE=1457'
for period in (1,2,3):
 build=base/f'c-fused-lean-period{period}-build'
 out=base/f'c-fused-lean-period{period}'
 assert not out.exists()
 env=dict(os.environ,RR_BUILD_OUT=str(build),VERIFY_DEFINES=flags+f' -DVERIFY_FRAME_PERIOD={period}'+(' -DVERIFY_SKIP_RENDER' if period==1 else ''))
 subprocess.run(['bash','tools/build.sh'],env=env,check=True,stdout=subprocess.DEVNULL)
 env.update(SLAVE=str(build/'RoadRash-verify.slave'),AMIGA_SETUP='a1200-fast',WHD_ARGS='Cache CUSTOM2=1',DEBUG_PORT='26856',RR_TAPE='1',RR_TAPE_PATH=str(Path.cwd()/'tools/fixtures/c-attacks.json'),RR_CAPTURE='1457',RR_EVENTS_TEST='1',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
 with (base/f'c-fused-lean-period{period}.log').open('w') as log:
  subprocess.run([sys.executable,'tools/step_c.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
 reference=base/'c-fused-lean-state-v2'
 a=json.loads((reference/'step.json').read_text());b=json.loads((out/'step.json').read_text())
 n=min(a['steps'],b['steps'])-1
 assert (reference/'hashes.bin').read_bytes()[4:4*(n+1)]==(out/'hashes.bin').read_bytes()[4:4*(n+1)]
 assert a['sound_events']==b['sound_events']
 u=(reference/'step1457.bin').read_bytes();v=(out/'step1457.bin').read_bytes()
 for addr,size in [(0xa5d60,0x1180),(0xa5d50,16),(0xa5d1e,4),(0xa5d22,4),(0xa7220,8),(0xa59f4,2)]:
  assert u[addr-0xa5900:addr-0xa5900+size]==v[addr-0xa5900:addr-0xa5900+size],hex(addr)
 result=dict(period=period,hashes=n,sound_events_equal=True,snapshot_ranges_equal=6,frame_stats=b['frame_stats'])
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
