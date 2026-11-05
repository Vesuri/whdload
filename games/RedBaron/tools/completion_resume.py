from pathlib import Path
import os,sys,time,struct,json,hashlib
from types import SimpleNamespace
import route_status as r
ROOT=Path.cwd()
a=SimpleNamespace(out=Path('tmp/prof/completion-a2-a500-0'),machine='a500',mask=0)
def locate(name,off,targets):
 for attempt in range(30):
  r.command('stop')
  for lo,hi in r.memory_regions():
   path=a.out/f'locate-{lo:x}.bin';r.command(f'gdb dump binary memory {path} {lo:#x} {hi:#x}');b=path.read_bytes()
   pos=0
   while True:
    pos=b.find(b'\x4e\xf9',pos)
    if pos<0:break
    if pos+6*len(targets)<=len(b):
     base=struct.unpack_from('>I',b,pos+2)[0]-targets[0]
     if base>0 and all(b[pos+6*j:pos+6*j+2]==b'\x4e\xf9' and struct.unpack_from('>I',b,pos+6*j+2)[0]==base+t for j,t in enumerate(targets)) and base+off==lo+pos:
      print(name,hex(base),flush=True);return base
    pos+=2
  r.command('cont');time.sleep(2)
 raise TimeoutError('Cannot locate '+name)

def keys(base,off,bitmap,route,sim=False):
 # Supply native queue input and a held bitmap; the original routine returns it.
 # No executable byte changes; all breakpoints removed before capture.
 cumulative=[];count=0
 for delay,key in route:count+=delay;cumulative.append((count,key))
 cmd=['delete','set $poll=0','set $hold=0','set $last=0',f'break *{base+off:#x}','commands','silent','set $poll=$poll+1','if $hold > 0','set $hold=$hold-1','if $hold == 0',f'set *(unsigned char*)({base+bitmap:#x}+$last)=0','end','end']
 for poll,key in cumulative:
  cmd += [f'if $poll == {poll}',f'set *(unsigned short*){base+bitmap-0x40:#x}={key>>8}',f'set *(unsigned short*){base+bitmap+0x80:#x}=2',f'set $last={key>>8}',f'set *(unsigned char*)({base+bitmap:#x}+$last)=1','set $hold=10','end']
 cmd += [f'if $poll < {count+12 if sim else count}','continue','end','end','continue','delete']
 raw=r.command('gdb '+'\n'.join(cmd));(a.out/('sim-keys.log' if sim else 'ps-keys.log')).write_text(raw)
 if 'ERROR' in raw:raise RuntimeError(raw)

ps=0xd00498
keys(ps,0x15b3a,0x2ba5c,[(100,0x440d)]+[(100,0x4209)]*4+[(100,0x440d),(100,0x4209),(100,0x440d)])
r.command('cont')
sim=locate('sim',0x1ef92,[0x309cc,0x30a4e,0x30aec])
route=[(100,0x4209),(100,0x440d),(50,0x5900)]+[(100,0x4209)]*5+[(100,0x440d)]+[(100,0x4e00)]*20+[(100,0x440d),(100,0x4209),(100,0x440d)]+[(100,0x4e00)]*20+[(100,0x440d),(100,0x4209),(100,0x440d)]+[(100,0x4209)]*5+[(100,0x440d)]
keys(sim,0x1ef92,0x30f8c,route,True)
raw=r.command(f'gdb delete\nbreak *{sim+0x21d30:#x}\ncontinue\ndelete');(a.out/'flight.log').write_text(raw)
sys.path.insert(0,str(ROOT/'tools'))
from completion_machines import environment
env=environment('a500',0);slave=ROOT/'tmp/build/RedBaron.slave'
meta=dict(machine=a.machine,mask=a.mask,sim=sim,ps=ps,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),environment={k:env[k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS']},route='External native keyboard return/held-bit fixture; removed before timing')
(a.out/'entry.json').write_text(json.dumps(meta,indent=2)+'\n')
print('NORMAL FLIGHT READY',a.out,flush=True)
