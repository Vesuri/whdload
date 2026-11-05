from pathlib import Path
import shutil,os,subprocess,sys
from matrix_a import config,cleanup
root=Path.cwd();src=root/'tmp/d-assets-capacity-source';shutil.copytree(root/'tmp/d-public-assets-v4-source',src)
p=src/'public_assets.s';s=p.read_text().replace(' bsr public_asset_publish_fixed\n bra .done', ''' move.l a3,-(a7)
 bsr public_asset_publish_fixed
 move.l (a7)+,a3
 move.l (a3),a1
 move.l -4(a1),a0
 bra .capacity_fail''',1);p.write_text(s)
build=root/'tmp/d-assets-capacity-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
env=config('040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(build/'RoadRash.slave'),DEBUG_PORT='27626',WHD_ARGS='CUSTOM2=1');out=root/'tmp/d-assets-capacity';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/assets_capacity_probe_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
finally:cleanup(out)
print(p.returncode)
