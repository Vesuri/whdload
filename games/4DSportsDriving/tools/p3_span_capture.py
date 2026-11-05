"""Capture native clipped span inputs and completed whole-bitmap outputs."""
import hashlib,json,os,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve(); meta=json.loads((cap/'anchor.json').read_text()); g=meta['game_base']; out=cap/'spans';out.mkdir();scratch=out/'scratch.bin'
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n):
 scratch.unlink(missing_ok=True); ans=command(f'gdb dump binary memory {scratch.relative_to(ROOT)} {addr:#x} {addr+n:#x}');b=scratch.read_bytes();assert len(b)==n,ans;return b
def u16(b,o):return struct.unpack_from('>H',b,o)[0]
def s16(b,o):return struct.unpack_from('>h',b,o)[0]
def u32(b,o):return struct.unpack_from('>I',b,o)[0]
command('stop'); command('gdb delete');results=[]
for i in range(int(os.environ.get('P3_CALLS','24'))):
 command(f'gdb break *{g+0x2c75c:#x}\nbreak *{g+0x2bfda:#x}\ncontinue');r=regs();kind={g+0x2c75c:'solid',g+0x2bfda:'two-colour'}[r['pc']];command('gdb delete')
 frame=read(r['a5']-0x3ac,0x3ac); f=frame[-0x80:]; data=read(r['a4']+0xbea,0x108);height=u16(f,0x54);y=s16(f,0x52);assert 0<height<=200 and 0<=y<200
 lo=u32(f,0x4a)-(r['a5']-0x3ac); ro=u32(f,0x4e)-(r['a5']-0x3ac); left=frame[lo:lo+height*2] if 0<=lo and lo+height*2<=len(frame) else read(u32(f,0x4a),height*2)
 right=frame[ro:ro+height*2] if 0<=ro and ro+height*2<=len(frame) else read(u32(f,0x4e),height*2)
 spans=list(zip(struct.unpack('>'+str(height)+'h',left),struct.unpack('>'+str(height)+'h',right)))
 planes=[u32(data,0x14+4*j) for j in range(data[0x11])];assert len(planes)==4 and u16(data,0xea)==40
 assert planes==[planes[0]+8000*j for j in range(4)]
 before=read(planes[0],32000)
 extra=read(r['a4']-0x3a3a,6)
 if os.environ.get('P3_STIPPLE')=='1' and kind=='solid':
  pattern=[0xaaaa5555,0xffff0000,0x80010000,0xffffffff][i%4]
  command(f'gdb set *(unsigned char*){r["a4"]-0x3a3a:#x}=1\nset *(unsigned int*){r["a4"]-0x3a38:#x}={pattern}')
  extra=bytes([1,extra[1]])+struct.pack('>I',pattern)

 entry={'synthetic_stipple':os.environ.get('P3_STIPPLE')=='1','kind':kind,'y':y,'height':height,'spans':spans,'colour':u16(f,0x56),'colour2':u16(f,0x58),'pattern':u32(f,0x5a),'stipple':extra[0]&1,'stipple_pattern':u32(extra,2),'write_mask':data[0x4c],'planes':planes,'registers':r}
 end=0x2cd44 if kind=='solid' else 0x2c632
 command(f'gdb tbreak *{g+end:#x}\ncontinue');rr=regs();assert rr['pc']==g+end and rr['a5']==r['a5']
 after=read(planes[0],32000)
 (out/f'{i:03}-before.bin').write_bytes(before);(out/f'{i:03}-after.bin').write_bytes(after);entry['changed_bytes']=sum(x!=z for x,z in zip(before,after));results.append(entry)
 (out/'cases.json').write_text(json.dumps(results,indent=2)+'\n'); print(i,kind,y,height,entry['colour'],entry['stipple'],entry['changed_bytes'],flush=True)
scratch.unlink(missing_ok=True)
