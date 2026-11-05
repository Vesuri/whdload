"""Private full native-step frame check, including signed rollback and neutral."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
root=Path('tmp/prof/c4-continued-loop-slow');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];stop=0x41000;sp=0x4f000
listing=Path('tmp/build/c4-continued-loop.lst').read_text(encoding='latin1');sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)};base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()}
images=[(addr,(root/f'timing-state-{name}.bin').read_bytes()) for name,addr in [('chip',0),('slow',0xc00000)]]
import sys
sys.path.insert(0,'tools')
from game_image import hunks
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
def invoke(addr):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,addr,stop,1000000,100000));assert reg(18)==stop and reg(8)==sp+4
import subprocess
old=subprocess.check_output(['git','show','7049f46:src/HardDrivinContact.s'],text=True);new=Path('src/HardDrivinContact.s').read_text()
addr=sy['_contact_pitch_rate_only']+0x1800;blobs=[]
for name,txt in [('old',old),('candidate',new),('forced','VERIFY_DISPATCH_NATIVE equ 1\n'+new)]:
 body=txt[txt.index('_contact_pitch_rate_only:'):txt.index('; Do not snap roll')]
 stem=Path('tmp/c4-pitch-rate-'+name);symbols='\n'.join('%s equ $%x'%(k,v) for k,v in sy.items() if k!='_contact_pitch_rate_only')
 stem.with_suffix('.s').write_text(f' org ${addr:x}\n'+('VERIFY_DISPATCH_NATIVE equ 1\n' if name=='forced' else '')+symbols+'\n'+body);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);blobs.append(stem.with_suffix('.bin').read_bytes())
cases=0;unchanged=0;retained=0
try:
 for raw in [-32768,-300,-181,-180,-179,-1,0,1,179,180,181,300,32767]:
  for n in [0,1,2,7,8,9,16,31]:
   for prior in [-7*65536-8192,0,5*65536+16384]:
    outputs=[];before=None
    for blob in blobs:
     for a,b in images:write(a,b)
     write(addr,blob);ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4);reg(6,0x4a000)
     reg(8,sp);pack(sp,'I',stop);pack(sp+4,'2h',raw,180);ok(u.uc_emu_start(h,a4-0x7f20,stop,1000000,100000));assert reg(18)==stop
     angle=reg(9)&65535
     if abs(raw)>180:assert angle==0
     reg(6,0x4a000);pack(0x49ffc,'h',raw);pack(sy['_time_scalar_fields'],'H',n)
     integer=abs(prior)//65536*(-1 if prior<0 else 1);pack(sy['_contact_rates']+8,'ihh',prior,integer,0);pack(a4-0x66ea,'h',integer)
     before=(read(sy['_contact_rates']+8,8),read(a4-0x66ea,2));reg(9,angle);invoke(addr)
     outputs.append((read(sy['_contact_rates']+8,8),read(a4-0x66ea,2)))
    assert outputs[0]==outputs[2],('forced',raw,n,prior)
    if n in [0,8] or abs(raw)<=180:assert outputs[0]==outputs[1],(raw,n,prior);unchanged+=1
    else:assert outputs[1]==before,(raw,n,prior);retained+=1
    cases+=1
 report=dict(passed=True,cases=cases,unchanged_cases=unchanged,retained_invalid_cases=retained,forced_native_cases=cases,scope='Actual native arcsine output and assembled old/candidate rear-contact helpers in captured game state: all valid inputs plus zero/eight intervals unchanged; undefined non-eight inputs preserve prior Q16 and native rates. Forced-native helper also matches all 312 old-source cases. Not whole trajectory or whole-build proof.')
 Path('tmp/c4-pitch-rate-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
