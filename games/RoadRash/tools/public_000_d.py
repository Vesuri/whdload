import os,sys,shutil,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');src=root/'tmp/d-public-000-source';shutil.copytree(root/'src',src,dirs_exist_ok=True)
p=src/'RoadRashHD.s';s=p.read_text().replace('\tIFD C_PUBLIC_MAIN\n\tbsr public_main_init\n\tENDC\n.no_c:',' .no_c:\n\tIFD C_PUBLIC_MAIN\n\tbsr public_main_init\n\tENDC');p.write_text(s)
p=src/'public_main.s';s=p.read_text().replace(' move.l _expmem(pc),a5',' move.l _enhanced_framerate(pc),d0\n beq .done\n move.l _expmem(pc),a5',1).replace(' lea public_main_spans(pc),a6',' move.l verify_c_selection+20(pc),d0\n cmpi.l #3,d0\n bne .helpers\n lea public_main_spans(pc),a6',1);p.write_text(s)
build=root/'tmp/d-public-000-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
rows=[]
for idx,(name,slave) in enumerate([('reference','d-main-promote-final-build'),('public','d-public-000-build')]):
 out=root/f'tmp/d-public-000-{name}';out.mkdir();env=config('a500-1m');env.update(FAST_KB='8192',SLAVE=str(root/'tmp'/slave/'RoadRash.slave'),DEBUG_PORT=str(27492+idx),WHD_ARGS='CUSTOM2=1')
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
 r=json.loads((out/'result.json').read_text());rows.append(dict(name=name,fps=r['fps'],distance=r['distance490']))
print(rows,flush=True)
