"""Fresh-boot ten-second constant-input timing window; debugger reads only."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--custom1',type=int,required=True);p.add_argument('--fields',type=int,default=500);p.add_argument('--profile',default='a500');p.add_argument('--cpu-policy',action='store_true');p.add_argument('--delay',type=int,default=0);p.add_argument('--expect-pause',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave')
s=Session(out,a.profile,out/'slave.slave',0x11664,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:]
 if a.custom1==0:
  from check_disabled import check
  disabled=check(out,['VERIFY_DRIVE','VERIFY_STEPINPUT','VERIFY_PHANTOM_ENTRY']);assert disabled['passed']
  (out/'disabled.json').write_text(json.dumps(disabled,indent=2)+'\n')
 hits={}
 if a.cpu_policy:
  for bank,b in s.dump_banks('policy'):
   for sig in [b'HDCPUP01',b'HDDISP01',b'HDSCAL01',b'HDTIME01',b'HDRPLAY1']:
    i=b.find(sig)
    if i>=0:assert sig not in hits;hits[sig]=bank+i+8
  assert len(hits)==5
  policy=hits[b'HDCPUP01'];ds=hits[b'HDDISP01'];scalar=hits[b'HDSCAL01']-10
  command(f'gdb dump binary memory {s.rel}/policy.bin {policy:#x} {policy+20:#x}')
  (out/'steps.bin').write_bytes(b'');(out/'timing.bin').write_bytes(b'')
  ts=hits[b'HDTIME01'];rp=hits[b'HDRPLAY1']
 for name in ['vbl.bin']:(out/name).write_bytes(b'')
 lines=[f'gdb break *{base+0x3f2:#x}',f'break *{base+0xcdb0:#x}',f'break *{base+0xe706:#x}','set $field=-1','set $physics=0','set $draws=0',f'while $field<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $field=$field+1']
 if a.cpu_policy:lines += [f'append binary memory {s.rel}/timing.bin {ts:#x} {ts+32:#x}',f'append binary memory {s.rel}/timing.bin {rp:#x} {rp+32:#x}']
 for r in regions:lines += [f'append binary memory {s.rel}/vbl.bin {r["base"]:#x} {r["base"]+r["size"]:#x}']
 lines += ['end',f'if $pc=={base+0xcdb0:#x} && $field>=0','set $physics=$physics+1','end',f'if $pc=={base+0xe706:#x} && $field>=0','set $draws=$draws+1','end','end','printf "COUNTS %d %d\\n",$physics,$draws','delete']
 if a.cpu_policy:
  at=lines.index('set $physics=$physics+1')+1
  lines[at:at]=[f'append binary memory {s.rel}/steps.bin {ds:#x} {ds+36:#x}',f'append binary memory {s.rel}/steps.bin {scalar:#x} {scalar+2:#x}']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 physics,draws=map(int,re.search(r'COUNTS (\d+) (\d+)',reply).groups())
 raw=(out/'vbl.bin').read_bytes();size=sum(r['size'] for r in regions);assert len(raw)==(a.fields+1)*size
 samples=[raw[i*size:(i+1)*size] for i in range(a.fields+1)]
 fronts=[struct.unpack_from('>I',b,0x7ffe-0x6a0e)[0] for b in samples]
 swaps=[i for i in range(1,len(fronts)) if fronts[i]!=fronts[i-1]]
 # Same exact PAL field duration used by the established capture reports.
 seconds=a.fields*0.020031887
 result=dict(fields=a.fields,seconds=seconds,swaps=len(swaps),fps=len(swaps)/seconds,mean_frame_ms=seconds*1000/len(swaps),swap_fields=swaps,physics_calls=physics,render_calls=draws,replay_fields=sum(bool(b[0x7ffe-0x5229]) for b in samples),crash_fields=sum(bool(b[0x7ffe-0x69fa]) for b in samples),input='Synthetic VERIFY_PHANTOM_ENTRY with native initialization and VERIFY_STEPINPUT controls; not qualification acceptance',custom1=a.custom1)
 if a.cpu_policy:
  command(f'gdb dump binary memory {s.rel}/policy-end.bin {policy:#x} {policy+20:#x}')
  tag,attn,terminator,single,pad,oversized=struct.unpack('>IIIHHI',(out/'policy-end.bin').read_bytes())
  step_raw=(out/'steps.bin').read_bytes();assert len(step_raw)==physics*38
  intervals=[];frame_steps=[];active_steps=0;previous=None
  for i in range(physics):
   row=step_raw[i*38:(i+1)*38];pending,consumed,steps,count,total,discarded=struct.unpack_from('>6I',row);n=struct.unpack_from('>H',row,36)[0]
   if not row[24]:continue
   active_steps+=1;intervals.append(n);frame_steps.append(count)
   if single:assert (pending,count,n)==(0,1,total),(i,pending,count,n,total)
   else:assert n<=8 and count>=1
   if previous is not None and steps==previous[0]+1:assert consumed-previous[1]==n,(i,consumed,previous,n)
   previous=(steps,consumed)
  if a.custom1:
   assert active_steps and oversized==0
   assert bool(single)==(not bool(attn&2))
  timing=(out/'timing.bin').read_bytes();assert len(timing)==(a.fields+1)*64
  timing=[timing[i:i+64] for i in range(0,len(timing),64)]
  paused=sum(bool(v[50]) for v in timing)
  if a.expect_pause:assert 0<paused<=a.expect_pause,(paused,a.expect_pause) # key consumed at the next controls pass
  for before,after in zip(timing,timing[1:]):
   delta=(struct.unpack_from('>I',after)[0]-struct.unpack_from('>I',before)[0])&0xffffffff
   assert delta==bool(after[28]),(delta,after[28])
   wall=(struct.unpack_from('>I',after,32)[0]-struct.unpack_from('>I',before,32)[0])&0xffffffff
   assert wall==(not after[50]),(wall,after[50])
  result['pause_fields']=paused
  result['cpu_policy']=dict(attnflags=attn,single=single,oversized_fallbacks=oversized,active_steps=active_steps,intervals=intervals,max_steps_per_frame=max(frame_steps,default=0))
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(dict(s.metadata,snapshot_size=size),indent=2)+'\n');print({k:v for k,v in result.items() if k!='swap_fields'},flush=True)
finally:s.close()
