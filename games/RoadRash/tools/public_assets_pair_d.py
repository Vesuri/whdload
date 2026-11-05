from pathlib import Path
import shutil,os,sys,subprocess,json
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');rows=[]
for flag in [0,1]:
 src=root/f'tmp/d-public-assets-pair-{flag}-source';shutil.copytree(root/'tmp/d-public-assets-v2-source',src)
 p=src/'public_assets.s';s=p.read_text().replace(' movem.l d0-d2/a0-a3,-(a7)\n', ' movem.l d0-d2/a0-a3,-(a7)\n move.w public_asset_enabled(pc),d0\n beq .done\n');s+=f'\npublic_asset_enabled: dc.w {flag}\n';p.write_text(s)
 build=root/f'tmp/d-public-assets-pair-{flag}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
 for cell in ['a1200-fast','060-50','a500-1m']:
  env=config(cell);env.update(SLAVE=str(build/'RoadRash.slave'),DEBUG_PORT=str(27594+flag),WHD_ARGS='CUSTOM2=1')
  if cell=='a500-1m':env['FAST_KB']='8192'
  out=root/f'tmp/d-public-assets-pair-{flag}-{cell}';out.mkdir()
  try:
   with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
  finally:cleanup(out)
  assert not p.returncode,(flag,cell)
  r=json.loads((out/'result.json').read_text());row=dict(flag=flag,cell=cell,fps=r['fps']);rows.append(row);print(row,flush=True)
(root/'tmp/d-public-assets-pair.json').write_text(json.dumps(rows,indent=2)+'\n')
