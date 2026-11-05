import ast,os,subprocess,sys
from pathlib import Path
root=Path.cwd();tree=ast.parse(Path('tools/approved_lane_cadences_c.py').read_text());base=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='base' for t in n.targets));base=base.replace('-DSTEP_CAPTURE=1457','-DSTEP_HASH_RING -DSTEP_CAPTURE_END')
kind=sys.argv[1];out=root/f'tmp/c-approved-lane-finish-{kind}';build=root/f'tmp/c-approved-lane-full-{kind}-build'
env=dict(os.environ,RR_SOURCE=str(root/'tmp/c-approved-lane-layout-source'),RR_BUILD_OUT=str(build),VERIFY_DEFINES=base+' -DVERIFY_FRAME_PERIOD=4'+(' -DVERIFY_FRAME_PATTERN' if kind=='vary' else ''))
subprocess.run(['bash','tools/build.sh'],env=env,check=True)
assert (build/'RoadRash.slave').read_bytes()==(root/'tmp/c-approved-lane-layout-build/RoadRash.slave').read_bytes()
env.update(SLAVE=str(build/'RoadRash-verify.slave'),RR_RESTART='1',RR_ROAD_LISTING=str(build/'RoadRash-verify.lst'),RR_TAPE_PATH=str(root/'tmp/c-raster-road-driven-race/driven-tape.json'),EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
subprocess.run([sys.executable,'tools/full_race_c.py',str(out)],env=env,check=True,timeout=600)
