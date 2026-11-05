#!/usr/bin/env python3
"""Read-only diagnostic runner. Requires VERIFY slave and CUSTOM2 nonzero.
Usage: verify_run.py OUT [takeoff|hover|combat|state|mission]
"""
import collections,hashlib,json,os,statistics,struct,sys
from pathlib import Path
from session_a import Session
from layout import locate
from route import run
from flight_profile import ROUTE,window

def marker(mem):
 hits=[];pos=0
 while True:
  pos=mem.find(b'GSVFY001',pos)
  if pos<0:break
  words=struct.unpack_from('>15I',mem,pos+8)
  if words[0] and words[13] and words[14] in (2048,8192):hits.append((pos+0x200000,words))
  pos+=8
 if len(hits)!=1:raise RuntimeError(f'expected one live marker, got {len(hits)}')
 addr,w=hits[0]
 return dict(address=addr,hunks=list(w[:9]),frames=w[9],entries=w[10],overflow=w[11],checkpoint=w[12],log=w[13],capacity=w[14])

def readlog(s,M):
 w=struct.unpack('>5I',s.read(M['address']+44,20));n=w[0]
 if w[2]:raise RuntimeError(f'frame log overflow: {w[2]}')
 return [list(x) for x in struct.iter_unpack('>IHH',s.read(M['log'],n*8))]

def snapshot(s,M):
 # Full hunks retain raw evidence; the regression gate compares them strictly.
 return {f'h{i}':s.read(a,(int.from_bytes(s.read(a-8,4),'big')-8)) for i,a in enumerate(M['hunks']) if i in (0,2,4,5,6)}

def save_snapshot(s,M,p):
 p.mkdir(parents=True,exist_ok=True)
 # Retain the complete fast-RAM state, including pointer-backed mission/object allocations.
 (p/'fast.bin').write_bytes(s.read(0x200000,0x800000))
 for n,b in snapshot(s,M).items():(p/f'{n}.bin').write_bytes(b)
 d=M['hunks'][6];h2=M['hunks'][2]
 ptr=int.from_bytes(s.read(d+0x45c8,4),'big')
 (p/'mission.bin').write_bytes(s.read(ptr,0xac))
 for off in (0x1ca6,0x1d0c,0x45e2):
  # Tables at 1ca6/1d0c are inline. Alive flags at 45e2 are pointer-backed.
  if off==0x45e2:
   ptr=int.from_bytes(s.read(d+off,4),'big');(p/'alive.bin').write_bytes(s.read(ptr,256))
 return dict(tick=int.from_bytes(s.read(d+0x3b94,2),'big'),vbl=int.from_bytes(s.read(h2+0x1c,4),'big'))

def main():
 out=Path(sys.argv[1]);mode=sys.argv[2] if len(sys.argv)>2 else 'takeoff'
 s=Session(out)
 try:
  route=list(ROUTE)
  if os.environ.get("MENU_DELAY"):route.insert(7,"f:"+os.environ["MENU_DELAY"])
  run(s,route)
  if mode=='combat':
   probe=marker(s.read(0x200000,0x800000))
   s.cmd(f"break *{probe['checkpoint']:#x}")
   s.cmd(f"condition $bpnum *(unsigned short*){probe['hunks'][6]+0x3b94:#x} >= 104")
   s.cmd('continue',timeout=600);s.cmd('delete')
   assert int.from_bytes(s.read(probe['address']+68,4),'big')==1,'CUSTOM3=1 fixture not applied'
   s.tap(7,hold=4,after=4)
   s.shot('start.png')
  if mode=='hover':
   window(s,s.fields)
   for _ in range(3):s.tap('f3',hold=4,after=30)
   s.fields(300)
  mem=s.read(0x200000,0x800000);M=marker(mem);M.update(locate(mem))
  provenance=dict(machine=os.environ.get('MACHINE','a500-fast'),whd_args=os.environ.get('WHD_ARGS',''),instrument=os.environ.get('INSTRUMENT','fields'),menu_delay=os.environ.get('MENU_DELAY','0'),hashes={})
  from session_a import FSUAE
  for name,path in [('emulator',FSUAE),('runtime_slave',s.run/'dh1/Gunship.slave'),('source',Path(__file__).resolve().parents[1]/'src/GunshipHD.s'),('verify_module',Path(__file__).resolve().parents[1]/'src/verify.i')]:
   provenance['hashes'][name]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
  (s.out/'provenance.json').write_text(json.dumps(provenance,indent=2))
  (s.out/'layout.json').write_text(json.dumps(M,indent=2))
  (s.out/'fast.bin').write_bytes(mem)
  initial=save_snapshot(s,M,s.out/'initial')
  if mode=='state':
   s.cmd(f"break *{M['checkpoint']:#x}")
   tickaddr=M['hunks'][6]+0x3b94
   s.cmd(f'condition $bpnum *(unsigned short*){tickaddr:#x} >= 100')
   for i in range(3):
    s.cmd('continue',timeout=600)
    clocks=save_snapshot(s,M,s.out/f'tick-{i}')
    (s.out/f'tick-{i}/clocks.json').write_text(json.dumps(clocks))
   s.cmd('delete')
  elif mode=='mission':
   pass
  else:
   before=readlog(s,M)
   instrument=os.environ.get('INSTRUMENT','fields')
   if instrument=='aprof':s.cmd('monitor aprof start')
   chunks=[]
   def advance(n):
    if n>100:
     for part in range(0,n,100):advance(min(100,n-part))
     return
    if instrument=='barto':
     f=s.out/f'chunk_{len(chunks):03d}.bin';s.profile(n-1,f);chunks.append(f)
    else:s.cmd(f'monitor fields {n-1}')
   
   v0=int.from_bytes(s.read(M['hunks'][2]+0x1c,4),'big')
   if mode=='takeoff':window(s,advance)
   elif mode=='hover':advance(500)
   elif mode=='combat':
    for _ in range(10):
     s.cmd('monitor button 1 1');advance(10)
     s.cmd('monitor button 1 0');advance(40)
   else:raise ValueError(mode)
   v1=int.from_bytes(s.read(M['hunks'][2]+0x1c,4),'big')
   if instrument=='aprof':s.cmd(f'monitor aprof stop {s.out / "window.prof"}')
   after=readlog(s,M);new=after[len(before):]
   intervals=[b[0]-a[0] for a,b in zip(new,new[1:])]
   result=dict(mode=mode,machine=os.environ.get('MACHINE','a500-fast'),start_vbl=v0,end_vbl=v1,frames=len(new),fps=50*len(new)/(v1-v0),interval_fields=intervals,frame_log=new,initial=initial,final=save_snapshot(s,M,s.out/'final'))
   result['ticks_per_second']=50*(result['final']['tick']-initial['tick'])/(v1-v0)
   result['pacing']=dict(interval_histogram_fields=dict(collections.Counter(intervals)),min_fields=min(intervals),max_fields=max(intervals),stddev_ms=20*statistics.pstdev(intervals))
   (s.out/'result.json').write_text(json.dumps(result,indent=2))
   (s.out/'clocks.txt').write_text(f"start {initial}\nend {result['final']}\n")
   print({k:result[k] for k in ('mode','machine','start_vbl','end_vbl','frames','fps','initial','final')},flush=True)
   assert v1-v0==500,(v0,v1)
   if chunks:
    from amigaxdev import barto
    hits=[];field=0
    for path in chunks:
     trace=barto.load(str(path))
     for f in trace.fields:
      for pc,cycles,regs in trace.instructions(f):
       if pc==M['hunks'][0]+0x44ca:hits.append(field)
      field+=1
    # Barto omits one lead-in field per chunk; a swap there is legitimately absent.
    assert 0 <= len(new)-len(hits) <= len(chunks),(len(hits),len(new),len(chunks))
    (s.out/'trace-check.json').write_text(json.dumps(dict(fields=field,trace_swaps=len(hits),logged_swaps=len(new),unrecorded_lead_in_fields=len(chunks),swaps_outside_trace=len(new)-len(hits),swap_fields=hits),indent=2))
  s.shot('end.png')
 finally:s.quit()
if __name__=='__main__':main()
