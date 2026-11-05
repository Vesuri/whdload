from pathlib import Path
import os,re,subprocess,shutil,hashlib,json
root=Path.cwd();source=root/'src';dest=root/'tmp/c3-cross-cost-source';dest.mkdir(exist_ok=True)
for p in source.glob('*.s'):shutil.copyfile(p,dest/p.name)
assert '_checkpoint_post:' not in (source/'HardDrivinCheckpoint.s').read_text(), 'Use authoritative build_reference after integration'
p=dest/'HardDrivinDispatch.s';p.write_text(p.read_text().replace('_dispatch_after_physics:\n','_dispatch_after_physics:\n bsr _private_checkpoint_post\n',1));p=dest/'HardDrivinTerrain.s';p.write_text(p.read_text()+Path('tools/c3_checkpoint_post.s').read_text())
flags=[]
for script in ['build_step4_all.sh','build_reference.sh']:
 flags += re.findall(r'-D\w+=\d+',Path('tmp',script).read_text())
flags+=['-DVERIFY_DRIVETRAIN_PHASE=1','-DVERIFY_TIME_SWEEP=1'];assert len(flags)==len(set(flags))
for window in ['a','b']:
 name='c3-cross-cost-'+window;out=root/'tmp/build'/name;defs=flags+(['-DVERIFY_STEPINPUT=1'] if window=='a' else [])
 args=[os.environ['VASM'],'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+str(source),'-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK']]+defs+['-o',str(out.with_suffix('.slave')),'-L',str(out.with_suffix('.lst')),'HardDrivinHD.s']
 subprocess.run(args,cwd=dest,check=True)
 manifest=dict(scope='Unseeded benchmark with private revised checkpoint post-query; exact normal controls/tape retained. Not authoritative source.',defines=defs,authoritative_source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.s')},private_source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.glob('*.s')},slave_sha256=hashlib.sha256(out.with_suffix('.slave').read_bytes()).hexdigest())
 out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
