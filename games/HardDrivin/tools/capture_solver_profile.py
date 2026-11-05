"""Ten-second trace of a selected solver build, with matching retained listing."""
import argparse,json,os,shutil
from capture_demo import ROOT,command,sha
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--listing',required=True);p.add_argument('--profile',default='a500');p.add_argument('--custom1',type=int,choices=[0,1,2],default=1);p.add_argument('--first-field',type=int,default=1);p.add_argument('--input-description',default='Build-dependent controls; inspect retained slave and listing');a=p.parse_args();assert a.first_field>=1;os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');shutil.copyfile(ROOT/'tmp/build'/a.listing,out/'slave.lst');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 print('Boot',a.name,flush=True);s.boot()
 if a.first_field>1:
  base=s.layout['code_base'];command(f'gdb break *{base+0x3f2:#x}\nset $skip=0\nwhile $skip<{a.first_field-1}\ncontinue\nset $skip=$skip+1\nend\ndelete')
 s.dump_banks('before');print('Capturing at race field',a.first_field,flush=True)
 (out/'profile-response.txt').write_text(command(f'profile 500 {out}/trace.bin'))
 s.metadata['trace_window']=dict(fields=500,first_full_race_field=a.first_field,anchor='race entry' if a.first_field==1 else 'VBL after input publication before requested field',input=a.input_description,listing_sha256=sha(out/'slave.lst'))
 (out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');s.dump_banks('after');print('Captured',a.name,flush=True)
finally:s.close()
