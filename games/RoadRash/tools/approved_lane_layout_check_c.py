import os,subprocess,sys,hashlib
from pathlib import Path
root=Path.cwd();base='-DVERIFY_C_GEOMETRY_REUSE_FORCE -DVERIFY_C_STEP -DVERIFY_C_STEERING -DVERIFY_C_OBJECT_FAST -DVERIFY_C_CACHE -DVERIFY_C_EVENTS -DVERIFY_C_SEED_RNG -DVERIFY_C_POSE_PREDICT -DPOSE_PREDICT_MEASURED -DVERIFY_C_PHYSICS_FAST -DVERIFY_C_PHYSICS_AUX -DVERIFY_C_FAST_STACK -DVERIFY_C_COLLISION_GEOMETRY -DVERIFY_C_LANE_SCAN -DVERIFY_C_FUSED_LEAN -DVERIFY_C_ROAD_TIMING -DSTEP_CAPTURE=1457'
normal=(root/'tmp/c-approved-lane-layout-build/RoadRash.slave').read_bytes()
for period in [4]:
 build=root/f'tmp/c-approved-lane-layout-period{period}-build';out=root/f'tmp/c-approved-lane-layout-period{period}-state'
 env=dict(os.environ,RR_SOURCE=str(root/'tmp/c-approved-lane-layout-source'),RR_BUILD_OUT=str(build),VERIFY_DEFINES=base+f' -DVERIFY_FRAME_PERIOD={period or 4}'+(' -DVERIFY_FRAME_PATTERN' if period==0 else '')+(' -DVERIFY_SKIP_RENDER' if period==1 else ''))
 subprocess.run(['bash','tools/build.sh'],env=env,check=True,stdout=subprocess.DEVNULL)
 assert (build/'RoadRash.slave').read_bytes()==normal
 env.update(SLAVE=str(build/'RoadRash-verify.slave'),RR_TAPE='1',RR_TAPE_PATH=str(root/'tools/fixtures/c-attacks.json'),RR_CAPTURE='1457',RR_EVENTS_TEST='1',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false',DEBUG_PORT=str(27204))
 subprocess.run([sys.executable,'tools/step_c.py',str(out)],env=env,check=True)
 subprocess.run([sys.executable,'tools/compare_short_c.py','tmp/c-approved-lane-width-period4-state',str(out)],check=True)
