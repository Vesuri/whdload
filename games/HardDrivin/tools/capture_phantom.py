"""Synthetic Phantom entry through native initialization; NOT qualification acceptance."""
import argparse,json,os,re,shutil,subprocess
from capture_demo import ROOT,command,sha
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('name');p.add_argument('--slave',default='s4-phantom-reference.slave');p.add_argument('--custom1',type=int,default=0);p.add_argument('--steps',type=int,default=108);p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);slave=ROOT/'tmp/build'/a.slave;shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x11664,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 print(a.name,flush=True);s.boot();base=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:];size=sum(r['size'] for r in regions)
 for k in ['physics','controls']:(out/(k+'.bin')).write_bytes(b'')
 lines=[f'gdb break *{base+0x7c32:#x}',f'break *{base+0xcdb0:#x}',f'break *{base+0x3f2:#x}','set $s3n=0','set $s3f=0',f'while $s3n < {a.steps}','continue',f'if $pc == {base+0x3f2:#x}','set $s3f=$s3f+1','end',f'if $pc == {base+0x7c32:#x}']
 lines += [f'append binary memory {s.rel}/controls.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += ['end',f'if $pc == {base+0xcdb0:#x}','printf "S3STEP %d %d\\n",$s3n,$s3f']
 lines += [f'append binary memory {s.rel}/physics.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += ['set $s3n=$s3n+1','end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[dict(step=int(i),field=int(f)) for i,f in re.findall(r'^S3STEP (\d+) (\d+)$',reply,re.M)];assert len(events)==a.steps
 meta=dict(s.metadata,snapshot_size=size,events=events,input='VERIFY_PHANTOM_ENTRY bypasses qualification but calls native challenge initialization. Constant native X=320 Y=200 buttons=4; reassert buttons before each controls call; compiled VERIFY_STEPINPUT fixture; verified captured inputs. No pose/velocity/clock/RNG writes.');(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 for k in ['physics','controls']:
  path=out/(k+'.bin');assert path.stat().st_size%size==0;(out/(k+'.sha256')).write_text(sha(path)+'\n');subprocess.run(['zstd','-q','-3',str(path)],check=True);path.unlink()
 print(events[-1],flush=True)
finally:s.close()
