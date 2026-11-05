import ast,os,subprocess,sys
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();tree=ast.parse(Path('tools/approved_lane_cadences_c.py').read_text());base=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='base' for t in n.targets));base=base.replace('-DSTEP_CAPTURE=1457','-DSTEP_HASH_RING -DSTEP_CAPTURE_END')+' -DREFERENCE_MOTION -DVERIFY_D_BUS_PRIORITY -DVERIFY_D_PUBLIC_MAIN'
os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,kind in enumerate(['fixed','vary']):
 build=root/f'tmp/d-complete-finish-{kind}-build';out=root/f'tmp/d-complete-finish-{kind}'
 env=dict(os.environ,RR_SOURCE=str(root/'src'),RR_BUILD_OUT=str(build),VERIFY_DEFINES=base+' -DVERIFY_FRAME_PERIOD=4'+(' -DVERIFY_FRAME_PATTERN' if kind=='vary' else ''))
 subprocess.run(['bash','tools/build.sh'],env=env,check=True,stdout=subprocess.DEVNULL)
 env=config('040-25');env.update(SLAVE=str(build/'RoadRash-verify.slave'),WHD_ARGS='CUSTOM2=1',DEBUG_PORT=str(27684+i),RR_RESTART='1',RR_ROAD_LISTING=str(build/'RoadRash-verify.lst'),RR_TAPE_PATH=str(root/'tmp/c-approved-motion-driven-finish/driven-tape.json'),EXTRA_ARGS=env['EXTRA_ARGS']+' --uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
 out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/full_race_c.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
subprocess.run([sys.executable,'tools/compare_full_c.py','tmp/d-complete-finish-fixed','tmp/d-complete-finish-vary'],check=True)

