"""Read-only input/physics entry and exit plus AFTER-input VBL snapshots."""
import argparse,json,os,re,shutil,subprocess
from capture_demo import ROOT,command,sha
from capture_session import Session
from state_fields import FIELDS
p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('name');p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False)
slave=ROOT/'tmp/build/s3-coupling.slave';shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay)
try:
 print('COUPLING',a.profile,a.delay,flush=True);s.boot();base=s.layout['code_base'];regions=s.layout['regions'][1:];size=sum(r['size'] for r in regions)
 hooks={0x3f2:'vbl',0x7c32:'controls_in',0x7dfa:'controls_out',0xcda4:'physics_in',0xcdb0:'physics_out'}
 for name in hooks.values():(out/(name+'.bin')).write_bytes(b'')
 lines=['gdb '+ '\n'.join('break *'+hex(base+off) for off in hooks),'set $hd_field=0','while $hd_field < 1251','continue']
 for off,name in hooks.items():
  lines+=['if $pc == '+hex(base+off)]
  if name=='vbl':lines+=['set $hd_field=$hd_field+1']
  lines += [f'printf "S3 {name} %d\\n", $hd_field']
  lines += [f'append binary memory {s.rel}/{name}.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[dict(kind=k,field=int(f)) for k,f in re.findall(r'^S3 (\w+) (\d+)$',reply,re.M)]
 meta=dict(s.metadata,snapshot_regions=regions,snapshot_size=size,events=events,vbl_hook='0x3f2 after input publication',fields=1251);(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 for name in hooks.values():
  path=out/(name+'.bin');assert path.stat().st_size==size*sum(e['kind']==name for e in events);digest=sha(path);subprocess.run(['zstd','-q','-3',str(path)],check=True);subprocess.run(['zstd','-qt',str(path)+'.zst'],check=True);(out/(name+'.sha256')).write_text(digest+'\n');path.unlink()
 print({name:sum(e['kind']==name for e in events) for name in hooks.values()},flush=True)
finally:s.close()
