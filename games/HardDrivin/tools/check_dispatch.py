import argparse,json,os,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-dispatch-live.slave');p.add_argument('--steps',type=int,default=150);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];hits={}
 for bank,b in s.dump_banks('dispatch'):
  for sig in [b'HDDISP01',b'HDTIME01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 assert len(hits)==2;ds=hits[b'HDDISP01'];ts=hits[b'HDTIME01']
 for name in ['dispatch.bin','time.bin']:(out/name).write_bytes(b'')
 lines=[f'gdb break *{base+0x10f28:#x}',f'break *{base+0x7c32:#x}',f'break *{base+0xe706:#x}','set $n=0','set $keys=0','set $draws=0',f'while $n<{a.steps}','continue',f'if $pc=={base+0x7c32:#x}',f'if *(unsigned char*){ts+28:#x} != 0','set $keys=$keys+1','end','end',f'if $pc=={base+0xe706:#x}',f'if *(unsigned char*){ts+28:#x} != 0','set $draws=$draws+1','end','end',f'if $pc=={base+0x10f28:#x}',f'append binary memory {s.rel}/dispatch.bin {ds:#x} {ds+32:#x}',f'append binary memory {s.rel}/time.bin {ts:#x} {ts+32:#x}','set $n=$n+1','end','end','printf "COUNTS %d %d\\n",$keys,$draws','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);raw=(out/'dispatch.bin').read_bytes();tim=(out/'time.bin').read_bytes();assert len(raw)==len(tim)==a.steps*32
 rows=[];last_consumed=0;last_pass=0;maxsteps=0;held=None
 for i in range(a.steps):
  pending,consumed,steps,frame_steps,frame_fields,discarded,active,first,buttons,mouse,pad=struct.unpack_from('>6I2B3H',raw,i*32)
  fields,previous,elapsed,observed,passes,T,ret,act,susp,r0,r1=struct.unpack_from('>7I4B',tim,i*32)
  taken=consumed-last_consumed;assert 0<=taken<=8 and T==taken*8192,(i,taken,T)
  assert steps==i+1 and not discarded and pending+consumed==observed,(i,pending,consumed,observed)
  assert bool(frame_steps==1)==bool(passes!=last_pass)
  if frame_steps==1:held=(buttons,mouse)
  assert (buttons,mouse)==held
  rows.append(dict(pass_index=passes,substep=frame_steps,elapsed=elapsed,taken=taken,pending=pending,consumed=consumed,buttons=buttons,mouse=mouse))
  last_consumed=consumed;last_pass=passes;maxsteps=max(maxsteps,frame_steps)
 import re
 keys,draws=map(int,re.search(r'COUNTS (\d+) (\d+)',reply).groups());assert keys==last_pass;assert draws==last_pass-1,(draws,last_pass)
 # Count live E706 calls only; replay rendering is a suspended timing epoch.
 r=dict(passed=True,substeps=a.steps,outer_frames=last_pass,max_substeps=maxsteps,keyboard_calls=keys,render_calls=draws,consumed_fields=last_consumed,discarded_fields=0,events=rows)
 (out/'results.json').write_text(json.dumps(r,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');print({k:v for k,v in r.items() if k!='events'})
finally:s.close()
