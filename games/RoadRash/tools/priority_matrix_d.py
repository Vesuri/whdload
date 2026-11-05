"""Equal-layout diagnostic priority controls, including native fallback machines."""
import json,os,subprocess,sys,shutil
from pathlib import Path
from matrix_a import config,CELLS,cleanup
root=Path.cwd();src=root/'src';dst=root/'tmp/d-priority-source';shutil.copytree(src,dst)
p=dst/'RoadRashHD.s';s=p.read_text();s=s.replace('pl_main\n\tPL_START\n\tPL_IFC2','pl_main\n\tPL_START\n\tPL_IFC2\n\tIFD D_PRIORITY\n\tPL_PSS $28C4C,d_priority_start,4\n\tENDC',1)
s+='''
 IFD D_PRIORITY
 IFND VERIFY
 FAIL "Priority experiment requires VERIFY"
 ENDC
d_priority_start:
 move.w #D_PRIORITY,$dff096
 move.l #$87040,$a5916
 rts
 ENDC
''';p.write_text(s)
p=dst/'simulation.s';s=p.read_text()
for label in ['step_reset','step_prepare']:s=s.replace(label+':\n',label+':\n\tIFD D_PRIORITY\n\tmove.w #D_PRIORITY,$dff096\n\tENDC\n',1)
p.write_text(s)
os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for tag,value in [('on',0x8400),('off',0x400)]:
 build=root/f'tmp/d-priority-{tag}-build'
 subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(dst),RR_BUILD_OUT=str(build),VERIFY_DEFINES=f'-DC_SIMULATION -DD_PRIORITY={value}'),check=True,stdout=subprocess.DEVNULL)
a=(root/'tmp/d-priority-on-build/RoadRash-verify.slave').read_bytes();b=(root/'tmp/d-priority-off-build/RoadRash-verify.slave').read_bytes();assert len(a)==len(b);diff=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y];assert len(diff)==3 and all(a[i]==0x84 and b[i]==4 for i in diff),diff
out=root/'tmp/d-priority-matrix';out.mkdir();rows=[]
for cell in [c for c in CELLS if not c.endswith('-mmu')]:
 for tag in ['on','off']:
  env=config(cell);env.update(SLAVE=str(root/f'tmp/d-priority-{tag}-build/RoadRash-verify.slave'),DEBUG_PORT='27350');env['WHD_ARGS']+=' CUSTOM2=1'
  dest=out/cell/tag;dest.mkdir(parents=True)
  try:
   with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/check_a.py',str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  finally:cleanup(dest)
  assert p.returncode==0,(cell,tag)
  r=json.loads((dest/'result.json').read_text());bit=0x400 if tag=='on' else 0
  assert r['before']['dma_frame']&0x400==bit and r['after']['dma_frame']&0x400==bit
  row=dict(cell=cell,priority=tag,fps=r['fps'],distance=r['distance490'],dma=r['after']['dma_frame']);rows.append(row);(out/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
