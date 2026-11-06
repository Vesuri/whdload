#!/usr/bin/env python3
"""Deterministic cold-boot TFX flight replay and paired-checkpoint comparison."""
import argparse, collections, hashlib, json, os, re, shutil, struct, sys, signal, threading
from pathlib import Path
from tfx import server
from amigaxdev.gdbserve import require_harness
from amigaxdev import barto
ROOT=Path(server.root)
# FLIGHT_TAPE selects another tape (e.g. tools/views.tape.json); default unchanged.
TAPE=Path(os.environ.get('FLIGHT_TAPE',ROOT/'tools/flight.tape.json')).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hunks(p):
 d=Path(p).read_bytes();o=4
 def word():
  nonlocal o
  x=struct.unpack_from('>I',d,o)[0];o+=4;return x
 assert word()==0
 n,first,last=word(),word(),word();sizes=[word()*4 for _ in range(last-first+1)];hs=[]
 while o<len(d):
  t=word()&0x3fffffff
  if t in (1001,1002):
   size=word()*4;hs.append(dict(size=size,bytes=d[o:o+size],relocs=[]));o+=size
  elif t==1003:hs.append(dict(size=word()*4,bytes=b'',relocs=[]))
  elif t==1004:
   while (cnt:=word()):
    dest=word();hs[-1]['relocs'] += [word() for _ in range(cnt)]
  elif t in (1008,):
   while (cnt:=word()):o+=cnt*4+4
  elif t==1009:
   count=word();o+=count*4
  elif t==1010:pass
  else:raise ValueError((hex(t),hex(o)))
 return hs

def run(machine,out,seed,observer=None,variant=None):
 out.mkdir(parents=True)
 shutil.copy(__file__,out/'replay_flight.py')
 variant=variant or dict(executable='TFX' if machine=='020' else 'tfx.020',custom3=0 if machine=='020' else 3,custom4=18,swap=0x18a6 if machine=='020' else 0x19fc)
 executable=ROOT/'tmp/game/TFX_v2.1_AGA/TFXAGA/data'/variant['executable']
 hs=hunks(executable)
 extra='--zorro_iii_memory=32768 --fast_memory=0'
 if machine=='040' and '--uae_cpu_frequency=' not in variant.get('extra_args',''):extra+=' --uae_cpu_frequency=40000000'
 if machine=='030':extra+=' --uae_fpu_model=68882'
 extra+=' '+variant.get('extra_args','')
 if machine=='020':extra+=' --cpu=68020' # full address bus for 32 MB Z3 RAM
 env=dict(FSUAE=os.environ.get('FSUAE',os.path.expanduser('~/.local/share/amiga/fs-uae-arm/fs-uae')),WINDOW='none',WARP='1',DETERMINISTIC='1',JOY0='none',JOY1='none',HDF='1',HDF_SEED=str(seed),AMIGA_SETUP='a1200-fast' if machine=='020' else 'a1200-'+machine,EXTRA_ARGS=extra,WHD_ARGS=f"CUSTOM3={variant['custom3']} CUSTOM4={variant['custom4']}",SLAVE=str(Path(os.environ.get('PROFILE_SLAVE',ROOT/'tmp/build/release/TFX.Slave')).resolve()),FPSP040=str(ROOT/'tmp/build/release/fpsp040.Slave'),FPSP060=str(ROOT/'tmp/build/release/fpsp060.Slave'))
 if 'custom5' in variant:env['WHD_ARGS']+=f" CUSTOM5={variant['custom5']}"
 if variant.get('custom1'):env['WHD_ARGS']+=f" CUSTOM1={variant['custom1']}"
 for key,name in [('SLAVE','slave.slave'),('FPSP040','fpsp040'),('FPSP060','fpsp060')]:
  shutil.copyfile(env[key],out/name);env[key]=str(out/name)
 server.profile_window=False;g=server.boot(env)
 (out/'launch.json').write_text(json.dumps({'machine':machine,'variant':variant,'env':env,'executable_sha256':sha(executable),'slave_sha256':sha(env['SLAVE']),'emulator_sha256':sha(env['FSUAE']),'seed_sha256':{n:sha(seed/n) for n in ['dh0.hdf','dh1.hdf']}},indent=2))
 log=(out/'debugger.log').open('w')
 def cmd(s):
  log.write('> '+s+'\n');log.flush()
  # A strict host watchdog also handles continuous emulator log output.
  expired=threading.Event()
  def timeout():
   expired.set();g.p.send_signal(signal.SIGINT)
  timer=threading.Timer(180,timeout);timer.start()
  try:r=g.cmd(s,timeout=90)
  finally:timer.cancel()
  if expired.is_set():raise TimeoutError(s)
  log.write(r+'\n');log.flush()
  if any(x in r.lower() for x in ('error','not supported','disconnected','invalid hex')):raise RuntimeError(r[-1000:])
  return r
 def dump(name,addr,size):
  p=out/name;cmd(f'dump binary memory {p.relative_to(ROOT)} {addr:#x} {addr+size:#x}');assert p.stat().st_size==size;return p.read_bytes()
 try:
  require_harness(g,'fields','key','input')
  cmd('monitor fields 1500');print(machine,out.name,'enrolment',flush=True)
  chip=dump('locate-chip.bin',0,0x200000);fast=dump('locate-fast.bin',0x40000000,0x2000000)
  def read(a,n):
   if a<0x200000:return chip[a:a+n]
   return fast[a-0x40000000:a-0x40000000+n]
  votes=collections.Counter();code=hs[0]['bytes'];rel=set(b for a in hs[0]['relocs'] for b in range(a,a+4))
  for off in range(0x1000,len(code)-32,4096):
   if any(a in rel for a in range(off,off+32)):continue
   sig=code[off:off+32];start=0
   if len(set(sig))<8:continue
   while (pos:=fast.find(sig,start))>=0:votes[0x40000000+pos-off]+=1;start=pos+1
  candidates=[]
  for base,n in votes.most_common():
   if n<3:continue
   if read(base-8,4)!=struct.pack('>I',hs[0]['size']+8):continue
   segs=[base];link=struct.unpack('>I',read(base-4,4))[0]*4
   for h in hs[1:]:
    if not link or len(read(link-4,4))!=4:break
    if not h['size']+8 <= struct.unpack('>I',read(link-4,4))[0] <= h['size']+0x100008:break
    segs.append(link+4);link=struct.unpack('>I',read(link,4))[0]*4
   if len(segs)==len(hs):candidates.append(segs)
  assert len(candidates)==1,(votes.most_common(5),candidates)
  bases=candidates[0]
  for a,h in zip(bases,hs):h['size']=struct.unpack('>I',read(a-8,4))[0]-8
  anchor=bases[0]+variant['swap']
  print('segments',*[hex(x) for x in bases],'anchor',hex(anchor),flush=True)
  (out/'segments.json').write_text(json.dumps(bases))
  # Stop before final Return starts the flight, so the first swap cannot be missed.
  tape=json.loads(TAPE.read_text())
  def key(raw):
   cmd(f'monitor key {raw:x} 1');cmd('monitor fields 8');cmd(f'monitor key {raw:x} 0')
  for i,k in enumerate(tape['enrolment']):
   key(k)
   if i<2:key(0x44);cmd('monitor fields 20')
  cmd(f'break *{anchor:#x}');cmd('monitor key 44 1')
  manifest={'machine':machine,'variant':variant,'executable_sha256':sha(executable),'env':env,'slave_sha256':sha(env['SLAVE']),'emulator_sha256':sha(env['FSUAE']),'tape_sha256':sha(TAPE),'fpsp040_sha256':sha(env['FPSP040']),'fpsp060_sha256':sha(env['FPSP060']),'seed_sha256':{n:sha(seed/n) for n in ['dh0.hdf','dh1.hdf']},'checkpoints':{}}
  for frame in range(1,max(tape['checkpoints'])+1):
   reply=cmd('continue')
   assert re.search(r'Breakpoint \d+, '+f'0x{anchor:08x}',reply),reply[-500:]
   cmd('maintenance flush register-cache')
   assert int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)==anchor
   if frame==1:
    cmd('monitor key 44 0')
    if observer is not None:
     observer(cmd,dump,bases,hs,out)
     break
   for event in tape['flight_inputs']:
    if event['swap']==frame:cmd(f"monitor input {event['event']} {event['value']}")
   if frame in tape['checkpoints']:
    prefix=f'swap-{frame:03d}';files=[]
    for i,(a,h) in enumerate(zip(bases,hs)):
     name=f'{prefix}-hunk{i}.bin';dump(name,a,h['size']);files.append(name)
    cmd('maintenance flush register-cache');(out/(prefix+'-regs.txt')).write_text(cmd('info registers'))
    trace=out/(prefix+'.trace');cmd(f'monitor profile 1 "" "{trace}"')
    t=barto.load(trace);png=out/(prefix+'.png');png.write_bytes(t.fields[-1].shot)
    files.append(png.name)
    manifest['checkpoints'][str(frame)]={name:sha(out/name) for name in files}
    print(machine,out.name,'swap',frame,sha(png)[:16],flush=True)
  (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 except Exception as error:
  (out/'failure.txt').write_text(repr(error))
  try:
   cmd('delete breakpoints')
   path=out/'failure.trace';cmd(f'monitor profile 1 "" "{path}"')
   t=barto.load(path);(out/('failure.png' if t.fields[-1].shot_kind else 'failure.jpg')).write_bytes(t.fields[-1].shot)
  except Exception as capture_error:
   (out/'failure-capture.txt').write_text(repr(capture_error))
  raise
 finally:
  shutil.copy(Path(server.run_dir)/'fsuae/Cache/Logs/debug.uae',out/'debug.uae')
  server.handle(g,'quit');log.close()
 return manifest

def main():
 p=argparse.ArgumentParser();p.add_argument('--machines',nargs='+',default=['040','020','030','060']);p.add_argument('--output',required=True);p.add_argument('--runs',type=int,default=2);p.add_argument('--clock-relative',action='store_true',help='accept explicitly reported absolute timer-origin translations');a=p.parse_args()
 os.chdir(ROOT);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
 shutil.copy(__file__,out/'replay_flight.py')
 shutil.copy(TAPE,out/'flight.tape.json')
 results={}
 for m in a.machines:
  runs=[run(m,out/f'{m}-{i+1}',out/f'{m}-seed') for i in range(a.runs)]
  from compare_flight import compare
  comparisons=[compare(out/f'{m}-1',out/f'{m}-{i+1}') for i in range(1,a.runs)]
  for i,r in enumerate(comparisons,2):(out/f'{m}-compare-1-{i}.json').write_text(json.dumps(r,indent=2))
  results[m]={'raw_identical':bool(comparisons) and all(r['raw_identical'] for r in comparisons),'clock_relative_identical':bool(comparisons) and all(r['clock_relative_identical'] for r in comparisons),'screenshots_identical':bool(comparisons) and all(r['screenshots_identical'] for r in comparisons)}
  (out/'comparison.json').write_text(json.dumps(results,indent=2))
 print(json.dumps(results,indent=2))
 if a.runs>1 and not all(r['clock_relative_identical' if a.clock_relative else 'raw_identical'] for r in results.values()):raise SystemExit(1)
if __name__=='__main__':main()
