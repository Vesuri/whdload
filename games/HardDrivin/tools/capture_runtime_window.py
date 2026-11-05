"""Fresh-boot ten-second constant-input timing window; debugger reads only."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--custom1',type=int,required=True);p.add_argument('--fields',type=int,default=500);p.add_argument('--profile',default='a500');p.add_argument('--cpu-policy',action='store_true');p.add_argument('--input-description',default='VERIFY_STEPINPUT constant controls');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave')
s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:]
 if a.custom1==0:
  from check_disabled import check
  disabled=check(out,['VERIFY_DRIVE','VERIFY_STEPINPUT']);assert disabled['passed']
  (out/'disabled.json').write_text(json.dumps(disabled,indent=2)+'\n')
 hits={}
 if a.cpu_policy:
  for bank,b in s.dump_banks('policy'):
   for sig in [b'HDCPUP01',b'HDDISP01',b'HDSCAL01',b'HDDRIVE1',b'HDFIXPT1',b'HDFRAC01',b'HDVECCH1',b'HDFORCE1']:
    i=b.find(sig)
    if i>=0:assert sig not in hits;hits[sig]=bank+i+8
  assert all(k in hits for k in [b'HDCPUP01',b'HDDISP01',b'HDSCAL01'])
  policy=hits[b'HDCPUP01'];ds=hits[b'HDDISP01'];scalar=hits[b'HDSCAL01']-10
  command(f'gdb dump binary memory {s.rel}/policy.bin {policy:#x} {policy+20:#x}')
  (out/'steps.bin').write_bytes(b'')
 for name in ['vbl.bin']:(out/name).write_bytes(b'')
 lines=[f'gdb break *{base+0x3f2:#x}',f'break *{base+0xcdb0:#x}',f'break *{base+0xe706:#x}','set $field=-1','set $physics=0','set $draws=0',f'while $field<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $field=$field+1']
 for r in regions:lines += [f'append binary memory {s.rel}/vbl.bin {r["base"]:#x} {r["base"]+r["size"]:#x}']
 lines += ['end',f'if $pc=={base+0xcdb0:#x} && $field>=0','set $physics=$physics+1','end',f'if $pc=={base+0xe706:#x} && $field>=0','set $draws=$draws+1','end','end','printf "COUNTS %d %d\\n",$physics,$draws','delete']
 if a.cpu_policy:
  at=lines.index('set $physics=$physics+1')+1
  lines[at:at]=[f'append binary memory {s.rel}/steps.bin {ds:#x} {ds+36:#x}',f'append binary memory {s.rel}/steps.bin {scalar:#x} {scalar+2:#x}']
 if a.custom1 and b'HDDRIVE1' in hits:
  dt=hits[b'HDDRIVE1'];lines.insert(1,f'break *{base+0xbad0:#x}')
  at=lines.index('continue')+1
  lines[at:at]=[f'if $pc=={base+0xbad0:#x}',f'printf "DRIVE_PITCH %d %d %d %d\\n",$field,*(unsigned int*){dt+12:#x},*(unsigned short*){dt+2:#x},*(unsigned short*){dt+6:#x}','end']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 physics,draws=map(int,re.search(r'COUNTS (\d+) (\d+)',reply).groups())
 raw=(out/'vbl.bin').read_bytes();size=sum(r['size'] for r in regions);assert len(raw)==(a.fields+1)*size
 samples=[raw[i*size:(i+1)*size] for i in range(a.fields+1)]
 fronts=[struct.unpack_from('>I',b,0x7ffe-0x6a0e)[0] for b in samples]
 swaps=[i for i in range(1,len(fronts)) if fronts[i]!=fronts[i-1]]
 # Same exact PAL field duration used by the established capture reports.
 seconds=a.fields*0.020031887
 result=dict(fields=a.fields,seconds=seconds,swaps=len(swaps),fps=len(swaps)/seconds,mean_frame_ms=seconds*1000/len(swaps),swap_fields=swaps,physics_calls=physics,render_calls=draws,replay_fields=sum(bool(b[0x7ffe-0x5229]) for b in samples),crash_fields=sum(bool(b[0x7ffe-0x69fa]) for b in samples),input=a.input_description,custom1=a.custom1)
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
  result['cpu_policy']=dict(attnflags=attn,single=single,oversized_fallbacks=oversized,active_steps=active_steps,intervals=intervals,max_steps_per_frame=max(frame_steps,default=0))
 if a.custom1 and b'HDDRIVE1' in hits:
  command(f'gdb dump binary memory {s.rel}/drivetrain-end.bin {dt:#x} {dt+16:#x}')
  interval,remaining,brake,active,calls,frames=struct.unpack('>4H2I',(out/'drivetrain-end.bin').read_bytes())
  pitches=[list(map(int,row)) for row in re.findall(r'DRIVE_PITCH (-?\d+) (\d+) (\d+) (\d+)',reply)]
  assert len(set(r[1] for r in pitches))==len(pitches),'duplicate engine pitch in one outer pass'
  assert all(r[3]==0 or (r[3]==1 and r[2]==1) for r in pitches),'intermediate pitch publication'
  result['drivetrain_reference']=dict(engine_calls=calls,outer_pairs=frames,active=active,remaining=remaining,original_interval=interval,pitch_publications=len(pitches),pitch_once_per_outer_pass=True)
 if b'HDFIXPT1' in hits:
  fx=hits[b'HDFIXPT1'];command(f'gdb dump binary memory {s.rel}/settled-end.bin {fx:#x} {fx+8:#x}')
  skipped,bulk=struct.unpack('>2I',(out/'settled-end.bin').read_bytes())
  result['settled']=dict(skipped_engine_fields=skipped,bulk_position_updates=bulk)
 if b'HDFRAC01' in hits:
  fr=hits[b'HDFRAC01'];command(f'gdb dump binary memory {s.rel}/fraction-end.bin {fr:#x} {fr+12:#x}')
  skipped,bulk,rate,active=struct.unpack('>2IhH',(out/'fraction-end.bin').read_bytes())
  result['fractional']=dict(skipped_engine_fields=skipped,bulk_position_updates=bulk,last_rate=rate,active_interval=active)
 if b'HDVECCH1' in hits:
  vc=hits[b'HDVECCH1'];command(f'gdb dump binary memory {s.rel}/vector-end.bin {vc:#x} {vc+8:#x}')
  vh,vm=struct.unpack('>2I',(out/'vector-end.bin').read_bytes());result['vector_cache']=dict(hits=vh,misses=vm)
 if b'HDFORCE1' in hits:
  fc=hits[b'HDFORCE1'];command(f'gdb dump binary memory {s.rel}/force-end.bin {fc:#x} {fc+12:#x}')
  fv,fp,fh,fm=struct.unpack('>2H2I',(out/'force-end.bin').read_bytes());result['force_cache']=dict(valid=fv,pending=fp,hits=fh,misses=fm)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(dict(s.metadata,snapshot_size=size),indent=2)+'\n');print({k:v for k,v in result.items() if k!='swap_fields'},flush=True)
finally:s.close()
