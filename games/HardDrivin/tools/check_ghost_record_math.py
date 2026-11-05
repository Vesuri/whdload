import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);name=sys.argv[1] if len(sys.argv)>1 else 's4-ghost-record-math';out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False)
shutil.copyfile(ROOT/'tmp/build/s4-ghost-record-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();hits=[]
 for bank,b in s.dump_banks('ghost-math'):
  i=b.find(b'HDGHRMT1')
  if i>=0:hits.append((bank+i+8,b[i+8:i+8+72+0x5300]))
 assert len(hits)==1;address,data=hits[0];meta=data[:72];glob=data[72:];base=address+72
 u32=lambda off:struct.unpack_from('>I',meta,off)[0]
 assert struct.unpack_from('>H',meta)[0]==1860 and u32(20)==0
 assert u32(4)==base+0x3000+3588 and u32(12)==base+0x2000+3588
 assert meta[8]==meta[16]==0
 assert u32(24+8)==1859*8 and u32(24+12)==310
 got=glob[0x2000:0x2000+3600];native=glob[0x3000:0x3000+3600]
 assert got==native,'full native history differs'
 expected=bytearray()
 for k in range(300):
  i=5+6*k if k<299 else 1859
  expected+=struct.pack('>6H',1000+7*i,60000-5*i,(i-500)&65535,700,(-700)&65535,16 if i&2 else 0)
 assert got==expected
 assert u32(48+8)==65535 and u32(48+12)==1365
 assert struct.unpack_from('>HHB',meta,48+16)==(23,8,255)
 left=[65535,0,-32768,700,-700,16];right=[0,65535,32767,-700,700,-17];expected=bytearray()
 for k in range(300):
  num=40+48*(k if k<299 else 1364);values=[]
  for j,(x,y) in enumerate(zip(left,right)):
   if j>=3:
    if y-x>720:y-=1440
    elif y-x < -720:y+=1440
   z=(x*(65535-num)+y*num)//65535
   if j>=3:
    if z>720:z-=1440
    elif z < -720:z+=1440
   values.append(z&65535)
  expected+=struct.pack('>6H',*values)
 assert glob[0x4000:0x4000+3600]==expected,'wide interval history differs'
 for lo,hi in [(0x2000+3600,0x3000),(0x3000+3600,0x4000),(0x4000+3600,0x52de)]:
  assert glob[lo:hi]==b'\x5a'*(hi-lo),(lo,hi)
 assert glob[0x1fff]==0
 result=dict(passed=True,native_calls=1860,native_emitted=310,native_cursor_phase_and_x_mismatches=0,full_history_bytes=3600,wide_interval=65535,wide_emitted=1365,guard_bytes_checked=2*(4096-3600)+(0x52de-0x4000-3600)+1)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
