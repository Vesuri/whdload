"""Bounded intro capture: retain 250 fields of DMA/screenshots, discard CPU words."""
from pathlib import Path
import os,sys,time,subprocess,re,struct,json,signal,gzip,hashlib
import numpy as np
from profile_window import command
root=Path.cwd();opt=sys.argv[1];tag=sys.argv[2];cap=root/('tmp/prof/intro-'+tag+'-c'+opt);cap.mkdir(exist_ok=False)
signal.signal(signal.SIGALRM,lambda *a: (_ for _ in ()).throw(TimeoutError('180-second watchdog')));signal.alarm(180)
assert not subprocess.run(['lsof','-nP','-iTCP:2471','-sTCP:LISTEN'],capture_output=True,text=True).stdout
slave=Path(os.environ.get('SLAVE',root/'tmp/build/4DSportsDriving.slave'));(cap/'slave.slave').write_bytes(slave.read_bytes())
log=(cap/'serve.log').open('w');env=dict(os.environ,SLAVE=str(slave),AMIGA_SETUP='a1200-040',SPLASH_DELAY='0',WHD_ARGS='CUSTOM2='+opt,DEBUG_PORT='2471',WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing')
p=subprocess.Popen(['python3','tools/driving.py','serve'],env=env,stdout=log,stderr=log)
try:
 deadline=time.monotonic()+120
 while 'serving on' not in (cap/'serve.log').read_text():assert time.monotonic()<deadline and p.poll() is None;time.sleep(.2)
 command('stop');command('gdb monitor fields 1600')
 f=cap/'memory.bin';command(f'gdb dump binary memory {f.relative_to(root)} 0x200000 0xa00000');b=f.read_bytes();mb=0x200000;candidates=[]
 for match in re.finditer(b'4DPERF!!',b):
  off=match.start();g=struct.unpack_from('>I',b,off+8)[0]
  if mb<=g<mb+len(b) and b[g-mb:g-mb+2]==b'\x4e\xf9':candidates.append(g)
 assert len(candidates)==1,candidates
 g=candidates[0];a=4*struct.unpack_from('>I',b,g-mb-4)[0]+4+0x7ffe
 (cap/'anchor.json').write_text(json.dumps(dict(game_base=g,data_base=a-0x7ffe,memory_base=mb,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest())))
 f.unlink();del b
 # Read a stable native intro frame boundary; no input or state modifications.
 command(f'gdb delete\ntbreak *{g+0x23024:#x}\ncontinue\nmaintenance flush register-cache')
 (cap/'start.txt').write_text(command('gdb info registers\np /u *(unsigned short*)($a5-4)'))
 rows=[]
 for part in range(25):
  raw=cap/'part.bin';command(f'gdb monitor profile 10 "" "{raw}"')
  with raw.open('rb') as inp:
   def u():return struct.unpack('<I',inp.read(4))[0]
   def blob():return inp.read(u())
   nf=u();ns=u();inp.seek(ns*4+16,1)
   for name in ('rom','chip','slow'):
    n=u()
    if part==0 and name=='chip':(cap/'chip.bin').write_bytes(inp.read(n))
    else:inp.seek(n,1)
   clock,unit=u(),u();assert nf==10
   for j in range(nf):
    idx=part*10+j;custom=blob();aga=blob();ds,dc=u(),u();dma=inp.read(ds*dc)
    dtype=np.dtype({'names':['reg','value','addr','type','extra'],'formats':['<u2','<u8','<u4','<i2','<u2'],'offsets':[0,2,12,29,31],'itemsize':ds});ar=np.frombuffer(dma,dtype=dtype)
    fetch=ar[(ar['type']==6)&(ar['reg']>=0x110)&(ar['reg']<0x118)];planes=[];screen=np.zeros(64000,dtype=np.uint8)
    for bit in range(4):
     pl=fetch[fetch['reg']==0x110+2*bit];planes.append(int(pl['addr'][0]));pixels=np.unpackbits(np.frombuffer(pl['value'].astype('>u2').tobytes(),dtype=np.uint8));assert len(pixels)==64000;screen|=pixels<<bit
    rs,rc=u(),u();inp.seek(rs*rc,1);cycles,idle,nw=u(),u(),u();inp.seek(nw*4,1);sz,kind=u(),u();shot=inp.read(sz)
    (cap/f'{idx:03}.jpg').write_bytes(shot)
    with gzip.open(cap/f'{idx:03}.dma.gz','wb',compresslevel=1) as out:out.write(dma)
    rows.append(dict(field=idx,part=part,dma_size=ds,planes=planes,colors=np.bincount(screen,minlength=16).tolist(),cpu_stores=int(((ar['type']==2)&((ar['reg']&0xff00)==0x1100)).sum()),blitter_stores=int(((ar['type']==5)&(ar['reg']==0)).sum()),cycles=cycles,idle=idle,custom=custom.hex()))
   assert inp.read(1)==b''
  raw.unlink()
  if part%5==0:print('Captured',len(rows),'fields',flush=True)
 (cap/'fields.json').write_text(json.dumps(rows,indent=2));print('Blue pixels min/max, zero fields:',min(r['colors'][1] for r in rows),max(r['colors'][1] for r in rows),sum(r['colors'][1]==0 for r in rows),flush=True)
finally:
 pid=int((root/'tmp/run/default/.run/fsuae.pid').read_text());state=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True).stdout;assert 'n'+str(root) in state,state
 command('quit');p.wait(timeout=15);log.close()
