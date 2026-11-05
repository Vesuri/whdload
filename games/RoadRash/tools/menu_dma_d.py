import os,sys,re,json,struct,collections
from harness_a import *
from drive import barto
listing=Path(os.environ['RR_ROAD_LISTING']).read_text(encoding='latin1')
def symbol(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
s=Session(sys.argv[1]);found=False
try:
 for attempt in range(1200):
  try:entry=rd(s,0x80000,2)
  except (ValueError,IndexError):entry=0
  if hasattr(s,'public_main_base'):
   slave=rd(s,0x8bdf2)-symbol('step_actor_road_copy')
   raw=read_bytes(s,slave+symbol('d_load_records'),12+40*40)
   if raw[:8]==b'RRDLOAD1':
    n=int.from_bytes(raw[8:12],'big')
    names=[raw[12+i*40+8:12+(i+1)*40].split(b'\0')[0].decode('latin1') for i in range(min(n,40))]
    if any(x.startswith('port') for x in names):found=True;break
  s.input('JOY2_FIRE_BUTTON',int(attempt%4==0));s.cmd('monitor fields 4')
 assert found
 s.input('JOY2_FIRE_BUTTON',0)
 rows=[]
 for idx in range(4):
  p=s.out/f'menu-{idx}.bin';s.cmd(f'monitor profile 19 "" "{p}"',timeout=120)
  trace=barto.load(str(p));counts=collections.Counter();suspect=[]
  for field in trace.fields:
   for i in range(0,len(field.dma),field.dma_size):
    addr=struct.unpack_from('<I',field.dma,i+12)[0];kind=struct.unpack_from('<h',field.dma,i+29)[0];counts[kind]+=1
    if kind not in (0,2) and 0x80000<=addr<0xbc3ec:suspect.append((addr,kind))
  (s.out/f'menu-{idx}.png').write_bytes(trace.fields[-1].shot)
  rows.append(dict(index=idx,counts=dict(counts),main_dma=sorted(set(suspect))))
  s.cmd('monitor fields 79')
 (s.out/'dma.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(rows,flush=True)
finally:s.quit()
