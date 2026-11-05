"""Read-only rendering window with independent renderer option and pointer audit."""
import argparse,json,os,shutil,struct,re
from capture_demo import ROOT,command,sha
from capture_session import Session
from count_demo_swaps import count
from machine_profiles import PROFILES
PROFILES["a1200-chip"]=("A1200","68EC020",2048,0,0,0,"swaps")
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--profile',default='a1200-020');p.add_argument('--render',type=int,default=0);p.add_argument('--request-render',type=int);p.add_argument('--custom1',type=int,default=1);p.add_argument('--custom2',type=int,default=0);p.add_argument('--window',choices=['A','B','attract'],default='A');p.add_argument('--fields',type=int,default=500);p.add_argument('--trace',action='store_true');p.add_argument('--mmu',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);src=ROOT/'tmp/build'/a.slave;shutil.copyfile(src,out/'slave.slave');shutil.copyfile(src.with_suffix('.lst'),out/'slave.lst')
s=Session(out,a.profile,out/'slave.slave',0x10844 if a.window=='attract' else 0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1} CUSTOM3={a.render if a.request_render is None else a.request_render} CUSTOM2={a.custom2}'
if a.mmu:
 assert a.profile.startswith('a4000-');s.env['CPU']=s.env['CPU'].replace('-NOMMU','')
try:
 print('BOOT',a.name,flush=True);s.boot();base=s.layout['code_base'];a4=s.layout['a4']
 if a.window=='B':command(f'gdb break *{base+0x3f2:#x}\nset $skip=0\nwhile $skip<3999\ncontinue\nset $skip=$skip+1\nend\ndelete')
 banks=s.dump_banks('before')
 def read(addr,n):
  for b,data in banks:
   if b<=addr and addr+n<=b+len(data):return data[addr-b:addr-b+n]
  raise ValueError(hex(addr))
 ptrs={k:struct.unpack('>I',read(a4-off,4))[0] for k,off in [('left',0x69e0),('right',0x69dc),('pattern',0x69e4),('front',0x6a0e),('back',0x6a12)]}
 assert ptrs['right']==ptrs['left']+400
 assert ptrs['front']<0x200000 and ptrs['back']<0x200000
 listing=(out/'slave.lst').read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 loaded=s.layout['published']-sym('_code_start')
 actual=struct.unpack('>I',read(loaded+sym('_render_options'),4))[0]
 assert actual==a.render,(actual,a.render)
 s.metadata['selected_render_options']=actual
 s.metadata['dispatch_cpu_single']=struct.unpack('>H',read(loaded+sym('_dispatch_cpu_single'),2))[0]
 s.metadata['render_window']=dict(window=a.window,fields=a.fields,custom1=a.custom1,custom3=a.render,custom2=a.custom2,pointers=ptrs,listing_sha256=sha(out/'slave.lst'))
 (out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n')
 if a.trace:
  (out/'profile-response.txt').write_text(command(f'profile {a.fields} {out}/trace.bin'));s.dump_banks('after')
 else:
  r=count(s,a.fields);(out/'render-result.json').write_text(json.dumps(dict(r,pointers=ptrs),indent=2)+'\n');print({k:v for k,v in r.items() if k!='per_field'},flush=True)
 if a.mmu:
  s.dump_banks('after');(out/'functional-only.json').write_text(json.dumps(dict(mmu=True,timing_valid=False,swaps=r['swaps'],fields=a.fields))+'\n')
 print('DONE',a.name,ptrs,flush=True)
finally:s.close()
