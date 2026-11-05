"""Capture native prepared bitmap blits, including masks and constant planes."""
import json,os,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];out=cap/'bitmaps';out.mkdir();scratch=out/'scratch.bin'
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n):
 scratch.unlink(missing_ok=True);command(f'gdb dump binary memory {scratch.relative_to(ROOT)} {addr:#x} {addr+n:#x}');b=scratch.read_bytes();assert len(b)==n;return b
def u16(b,o):return struct.unpack_from('>H',b,o)[0]
def s16(b,o):return struct.unpack_from('>h',b,o)[0]
def u32(b,o):return struct.unpack_from('>I',b,o)[0]
command('stop');command('gdb delete');results=[]
for i in range(int(os.environ.get('P3_CALLS','32'))):
 command(f'gdb break *{g+0x32242:#x}\ncondition $bpnum *(unsigned short*)($a4+0xcd4)==40 && *(unsigned char*)($a4+0xbfb)==4\ncontinue');r=regs();command('gdb delete');data=read(r['a4']+0xbea,0x108);params=read(r['a4']+0x21f0,30);desc=read(r['a5'],48);con=u16(read(r['a4']-0x32ec,2),0);planes=[u32(data,0x14+4*j) for j in range(4)];assert len(set(planes))==4,planes
 width=(r['d1']&63) or 64;height=((r['d1']&65535)>>6) or 1024;assert width<=21 and height<=200
 amod=s16(params,16);bmod=s16(params,14);dmod=s16(params,12);masks=[desc[12],desc[13]];groups=[]
 for v in desc[14:]:
  if v==0:break
  groups.append(v)
 else:raise AssertionError('unterminated plane list')
 nsrc=(height-1)*(2*width+bmod)+2*width;nmask=(height-1)*(2*width+amod)+2*width
 prefix=out/f'{i:03}';before=b''.join(read(p,8000) for p in planes);prefix.with_name(prefix.name+'-before.bin').write_bytes(before)
 if r['a1']:prefix.with_name(prefix.name+'-mask.bin').write_bytes(read(r['a1'],nmask))
 for j in range(len(groups)):prefix.with_name(prefix.name+f'-source{j}.bin').write_bytes(read(r['a0']+j*(r['d0']&65535),nsrc))
 entry={'planes':planes,'registers':r,'width':width,'height':height,'amod':amod,'bmod':bmod,'dmod':dmod,'afwm':u16(params,26),'alwm':u16(params,28),'shift':(r['d3']>>12)&15,'con0':con,'zero_planes':masks[0],'one_planes':masks[1],'source_planes':groups,'plane_mask':data[0x4c],'dest_offset':r['d2']&65535,'has_mask':bool(r['a1'])}
 command(f'gdb tbreak *{g+0x323a6:#x}\ncontinue');rr=regs()
 # DisownBlitter outside the primitive batch may leave the last DMA active.
 # Execute only the native DMACONR poll, then restore its PC/CCR effects.
 command(f'gdb set $pc={g+0x32228:#x}\ntbreak *{g+0x32242:#x}\ncontinue\nset $pc={rr["pc"]:#x}\nset $sr={rr["sr"]:#x}')
 after=b''.join(read(p,8000) for p in planes);prefix.with_name(prefix.name+'-after.bin').write_bytes(after);entry['changed_bytes']=sum(x!=y for x,y in zip(before,after));results.append(entry);(out/'cases.json').write_text(json.dumps(results,indent=2)+'\n');print(i,entry,flush=True)
scratch.unlink(missing_ok=True)
