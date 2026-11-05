from pathlib import Path
import shutil,os,sys,subprocess,json
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');rows=[]
for i,offset in enumerate([0x4e002,0x4e010,0x4e020,0x4e040]):
 src=root/f'tmp/d-assets-align-{offset:x}-source';shutil.copytree(root/'tmp/d-public-assets-v3-source',src)
 p=src/'public_main.s';s=p.read_text().replace('addi.l #$4b000,d0',f'addi.l #${offset-0x5000:x},d0');p.write_text(s)
 build=root/f'tmp/d-assets-align-{offset:x}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
 out=root/f'tmp/d-assets-align-{offset:x}';out.mkdir();env=config('060-50');env.update(SLAVE=str(build/'RoadRash.slave'),DEBUG_PORT=str(27614+i),WHD_ARGS='CUSTOM2=1')
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 assert not p.returncode,offset
 r=json.loads((out/'result.json').read_text());row=dict(offset=hex(offset),fps=r['fps']);rows.append(row);print(row,flush=True)
(root/'tmp/d-assets-align.json').write_text(json.dumps(rows,indent=2)+'\n')
