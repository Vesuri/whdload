import os,sys,shutil,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');src=root/'tmp/d-public-priority-source';shutil.copytree(root/'src',src)
p=src/'bus_priority.s';s=p.read_text().replace('\tbtst #3,verify_attn+3(pc) ; AFF_68040 also applies to 060\n\tbeq .done','\tnop\n\tnop\n\tnop\n\tnop\n\tnop').replace('move.w #$0400,$dff096','move.w #D_PRIORITY,$dff096',1);p.write_text(' IFND D_PRIORITY\nD_PRIORITY=$400\n ENDC\n'+s)
for kind,value in [('on',0x8400),('off',0x400)]:
 build=root/f'tmp/d-public-priority-{kind}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build),VERIFY_DEFINES=f'-DC_SIMULATION -DD_PRIORITY={value}'),check=True,stdout=subprocess.DEVNULL)
a=(root/'tmp/d-public-priority-on-build/RoadRash-verify.slave').read_bytes();b=(root/'tmp/d-public-priority-off-build/RoadRash-verify.slave').read_bytes();diff=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y];assert len(a)==len(b) and len(diff)==1 and a[diff[0]]==0x84 and b[diff[0]]==4,diff
out=root/'tmp/d-public-priority-matrix';out.mkdir();rows=[]
for cell in ['a1200-fast','a1200-fast+cache','a1200-fast+nocache','030-50','030-50+cache','040-25','040-25+cache','060-50','060-50+cache']:
 for kind in ['on','off']:
  dest=out/cell/kind;dest.mkdir(parents=True);env=config(cell);env.update(SLAVE=str(root/f'tmp/d-public-priority-{kind}-build/RoadRash-verify.slave'),DEBUG_PORT='27490');env['WHD_ARGS']+=' CUSTOM2=1'
  try:
   with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  finally:cleanup(dest)
  assert not p.returncode,(cell,kind)
  r=json.loads((dest/'result.json').read_text());bit=0x400 if kind=='on' else 0;assert r['before']['dma_frame']&0x400==bit and r['after']['dma_frame']&0x400==bit
  rows.append(dict(cell=cell,priority=kind,fps=r['fps'],dma=r['after']['dma_frame']));(out/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows[-1],flush=True)
