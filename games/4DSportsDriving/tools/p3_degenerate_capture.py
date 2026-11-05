"""Capture native clipped lines and completed planar results."""
import json,os,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];out=cap/'degenerate-lines';out.mkdir();scratch=out/'scratch.bin'
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def read(addr,n):
 scratch.unlink(missing_ok=True);command(f'gdb dump binary memory {scratch.relative_to(ROOT)} {addr:#x} {addr+n:#x}');b=scratch.read_bytes();assert len(b)==n;return b
command('stop');command('gdb delete');results=[]
for i in range(int(os.environ.get('P3_CALLS','32'))):
 command(f'gdb tbreak *{g+0x2ce62:#x} if *(unsigned short*)($a4+0xcd4)==40 && *(unsigned short*)($a4+0xcd6)==200\ncontinue');r=regs();assert r['pc']==g+0x2ce62
 data=read(r['a4']+0xbea,0x108);planes=list(struct.unpack_from('>4I',data,0x14));assert planes==[planes[0]+8000*j for j in range(4)]
 before=read(planes[0],32000)
 r['d7']=struct.unpack('>H',read(r['a0']+16,2))[0]
 if os.environ.get('P3_SYNTHETIC')=='1':
  deltas=[(63,17),(17,63),(-63,17),(-17,63),(63,-17),(17,-63),(-63,-17),(-17,-63),(63,0),(0,63),(0,0),(31,31)]
  dx,dy=deltas[i%len(deltas)];x=150+(i//len(deltas))*2;y=100
  for j,v in enumerate([x,y,x+dx,y+dy]):r[f'd{j}']=v
  r['d7']=i%16
  command('gdb '+'\n'.join(f'set $d{j}={r[f"d{j}"]}' for j in [0,1,2,3])+f'\nset *(unsigned short*){r["a0"]+16:#x}={r["d7"]}')
 entry={'xy':[r[f'd{j}']&65535 for j in range(4)],'colour':r['d7']&65535,'write_mask':data[0x4c],'registers':r}
 command(f'gdb tbreak *{g+0x2cf5a:#x}\ncontinue');rr=regs();assert rr['pc']==g+0x2cf5a and rr['sp']==r['sp']+20
 after=read(planes[0],32000);(out/f'{i:03}-before.bin').write_bytes(before);(out/f'{i:03}-after.bin').write_bytes(after);entry['synthetic_test_input']=os.environ.get('P3_SYNTHETIC')=='1';entry['changed_bytes']=sum(a!=b for a,b in zip(before,after));results.append(entry);(out/'cases.json').write_text(json.dumps(results,indent=2)+'\n');print(i,entry['xy'],entry['changed_bytes'],flush=True)
scratch.unlink(missing_ok=True)
