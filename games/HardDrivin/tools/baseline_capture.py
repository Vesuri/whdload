#!/usr/bin/env python3
"""Whole-window read-only state, front-buffer and event capture; archives raw snapshots."""
import argparse,hashlib,json,os,re,shutil,struct,subprocess
from pathlib import Path
from capture_demo import ROOT,command,sha
from capture_session import Session
from machine_profiles import PROFILES,banks
from state_fields import FIELDS

def capture(s,mode,n):
 code=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:]
 stream=s.out/'states.bin';stream.write_bytes(b'');frames=s.out/'fronts.bin';frames.write_bytes(b'')
 hook=0x44 if mode=='attract' else 0x3f2;initial=-1 if mode=='attract' else 0
 lean=s.env['SWAP_ONLY']=='1'
 extra_breaks='' if lean else '\n'.join(f'break *{code+off:#x}' for off in [0xb4,0xcdb0,0x10bb6])
 dumps='\n'.join(f'append binary memory {s.rel}/states.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions)
 script=f'''gdb break *{code+hook:#x}
{extra_breaks}
set $hd_f={initial}
while $hd_f < {n}
continue
if $pc == {code+hook:#x}
set $hd_f=$hd_f+1
{dumps}
set $hd_front=*(unsigned long*){a4-0x6a0e:#x}
eval "append binary memory {s.rel}/fronts.bin %u %u", $hd_front, $hd_front+32000
else
printf "EVENT %x %d\\n", $pc-{code:#x}, $hd_f
end
end
delete
'''
 reply=command(script);(s.out/'events.log').write_text(reply)
 events=[dict(offset=int(o,16),field=int(f)) for o,f in re.findall(r'^EVENT ([0-9a-f]+) (-?\d+)$',reply,re.M)]
 size=sum(r['size'] for r in regions);count=n+1 if mode=='attract' else n;assert stream.stat().st_size==count*size and frames.stat().st_size==count*32000
 rows=[];frontptrs=[]
 with stream.open('rb') as f,frames.open('rb') as g:
  for index in range(count):
   b=f.read(size);pic=g.read(32000);frontptrs.append(struct.unpack_from('>I',b,0x7ffe-0x6a0e)[0])
   rows.append(dict(field=index if mode=='attract' else index+1,state_sha256=hashlib.sha256(b).hexdigest(),front_sha256=hashlib.sha256(pic).hexdigest(),**{k:b[0x7ffe+off:0x7ffe+off+z].hex() for k,(off,z) in FIELDS.items()},attract=b[0x7ffe-0x69fc:0x7ffe-0x69fa].hex(),race=b[0x7ffe-0x522c:0x7ffe-0x522a].hex()))
 flips=[]
 previous=struct.unpack_from('>I',(s.out/'game-data.bin').read_bytes(),0x7ffe-0x6a0e)[0]
 for i,ptr in enumerate(frontptrs):
  if mode=='drive' or i>0:
   if ptr!=previous:flips.append(dict(offset=0xb4,field=i if mode=='drive' else i-1))
  previous=ptr
 if lean:events=flips
 else:assert flips==[e for e in events if e['offset']==0xb4 and e['field']>=0], 'front-pointer swap validation failed'
 windows=[('attract',0,1000)] if mode=='attract' else [('A',1,1251),('B',3000,5600)]
 result={}
 for name,lo,hi in windows:
  counts={label:sum(x['offset']==offset and lo<=x['field']<hi for x in events) for label,offset in [('swaps',0xb4),('physics',0xcdb0),('replay',0x10bb6)]}
  if lean:counts['physics']=None;counts['replay']=None
  result[name]=dict(first=lo,end=hi,seconds=(hi-lo)*142102/7093790,**counts,fps=counts['swaps']/((hi-lo)*142102/7093790))
 (s.out/'baseline.json').write_text(json.dumps(dict(mode=mode,fields=n,swap_method='VBL front-pointer changes' if lean else 'swap breakpoints, checked against VBL front-pointer changes',windows=result,events=events,per_field=rows),indent=2)+'\n')
 for p in [stream,frames]:
  digest=sha(p);subprocess.run(['zstd','-q','-3',str(p)],check=True);subprocess.run(['zstd','-qt',str(p)+'.zst'],check=True);(s.out/(p.name+'.sha256')).write_text(digest+'\n');p.unlink()
 print(s.profile,mode,result,flush=True)

def placement(s):
 b=(s.out/'game-data.bin').read_bytes();e=s.env
 def bank(addr):
  for name,base,size in banks(e):
   if base<=addr<base+size:return name
  return 'outside configured RAM'
 values={r['name']:r['base'] for r in s.layout['regions']}
 for name,off in [('edge_left',-0x69dc),('edge_right',-0x69e0),('patterns',-0x69e4),('front',-0x6a0e),('back',-0x6a12)]:values[name]=struct.unpack_from('>I',b,0x7ffe+off)[0]
 (s.out/'placement.json').write_text(json.dumps({k:dict(address=v,bank=bank(v)) for k,v in values.items()},indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('profile',choices=PROFILES);p.add_argument('mode',choices=['attract','drive']);p.add_argument('name');p.add_argument('--slave',type=Path);p.add_argument('--custom1',type=int,default=0);p.add_argument('--instant-blitter',action='store_true');a=p.parse_args();os.chdir(ROOT)
 out=ROOT/'tmp/prof'/a.name;assert out.parent==ROOT/'tmp/prof';out.mkdir(exist_ok=False)
 slave=a.slave.resolve() if a.slave else ROOT/'tmp/build'/('HardDrivin-verify.slave' if a.mode=='attract' else 'HardDrivin-drive.slave');shutil.copyfile(slave,out/'slave.slave')
 s=Session(out,a.profile,out/'slave.slave',0x10844 if a.mode=='attract' else 0x10ed4)
 s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
 if a.instant_blitter:s.env['EXTRA_ARGS']+=' --uae_immediate_blits=true'
 try:
  print('BOOT',a.name,flush=True);s.boot();placement(s);(out/'registers.txt').write_text(command('gdb info all-registers'));capture(s,a.mode,1000 if a.mode=='attract' else 5600)
 finally:s.close()
if __name__=='__main__':main()
