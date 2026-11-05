from pathlib import Path
import shutil,os,subprocess,sys,json
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');original=root/'src'
for kind in ['reference','public']:
 src=root/f'tmp/d-native-main-{kind}-source';shutil.copytree(original,src)
 p=src/'RoadRashHD.s';s=p.read_text()
 if kind=='public':s=s.replace('\tIFD C_PUBLIC_MAIN\n\tbsr public_main_init\n\tENDC\n.no_c:', '.no_c:\n\tIFD C_PUBLIC_MAIN\n\tbsr public_main_init\n\tENDC')
 s=s.replace('pl_main\n\tPL_START\n', 'pl_main\n\tPL_START\n IFD VERIFY_D_NATIVE_PACE\n PL_IFC2\n PL_PS $7736,verify_pace\n PL_ENDIF\n ENDC\n',1);p.write_text(s)
 if kind=='public':
  p=src/'public_main.s';s=p.read_text().replace(' move.l _expmem(pc),a5',' move.l _enhanced_framerate(pc),d0\n beq .done\n move.l _expmem(pc),a5',1).replace(' lea public_main_spans(pc),a6',' move.l verify_c_selection+20(pc),d0\n cmpi.l #3,d0\n bne .helpers\n lea public_main_spans(pc),a6',1).replace('.publish:\n','.publish:\n move.l a5,a1\n adda.l #$2876c,a1\n lea _base(pc),a0\n adda.l #step_stack_start-_base,a0\n move.w #$4ef9,(a1)\n move.l a0,2(a1)\n',1);p.write_text(s)
 build=root/f'tmp/d-native-main-{kind}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build),VERIFY_DEFINES='-DC_SIMULATION -DVERIFY_D_NATIVE_PACE -DVERIFY_C_SEED_RNG -DVERIFY_FRAME_PERIOD=8 -DVERIFY_HASH_FIELD=590'),check=True,stdout=subprocess.DEVNULL)
for i,kind in enumerate(['reference','public']):
 out=root/f'tmp/d-native-main-{kind}';out.mkdir();env=config('a500-1m');env.update(FAST_KB='8192',SLAVE=str(root/f'tmp/d-native-main-{kind}-build/RoadRash-verify.slave'),DEBUG_PORT=str(27556+i),WHD_ARGS='CUSTOM2=1',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--hash'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
