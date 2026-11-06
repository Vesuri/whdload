#!/usr/bin/env python3
"""Cold-boot baseline: fixed [2,252) vblank window, existing swap-indexed input tape."""
import argparse,csv,json,os,re,shutil,struct
from pathlib import Path
from replay_flight import ROOT,run,sha,TAPE
from amigaxdev import barto
VARIANTS={
 'integer':dict(executable='TFX',custom3=1,custom4=18,swap=0x18a6,publish=0x4a9bc,vblank=0x4b62a,clock=0x4bbd0),
 'original':dict(executable='TFX',custom3=1,custom4=22,swap=0x18a6,publish=0x4a9bc,vblank=0x4b62a,clock=0x4bbd0),
 'newfpu':dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,publish=0x4c474,vblank=0x4d2de,clock=0x4d884),
 'fpu':dict(executable='TFX.FPU',custom3=2,custom4=18,swap=0x16f6,publish=0x43d58,vblank=0x44c96,clock=0x4523c),
 'beta':dict(executable='TFX.040',custom3=4,custom4=18,swap=0x1632,publish=0x4a07c,vblank=0x4aece,clock=0x4b474),
}
START,END=2,252

def observer(v,end=END):
 def capture(cmd,dump,bases,hs,out):
  base=bases[0];ticks=0;swaps=1;events=[];inputs=[]
  tape=json.loads(TAPE.read_text())
  for name in ['publish','vblank']: 
   expected=bytes.fromhex('23c800dff080') if name=='publish' else bytes.fromhex('52b9')+struct.pack('>I',base+v['clock'])
   assert dump(name+'-opcode.bin',base+v[name],6)==expected
  def state(prefix):
   for i,(a,h) in enumerate(zip(bases,hs)):dump(f'{prefix}-hunk{i}.bin',a,h['size'])
   (out/(prefix+'-registers.txt')).write_text(cmd('info registers'))
  def cpuinfo(phase):
   info=cmd('monitor cpuinfo');(out/f'cpuinfo-{phase}.txt').write_text(info)
   fields=dict(re.findall(r'(\w+)=(\w+)',info))
   for key,value in v.get('expected_cpu',{}).items():assert int(fields[key])==value,(key,fields[key],value)
   return fields
  cpuinfo('entry')
  state('entry')
  cmd('delete breakpoints')
  markers={base+v[k]:k for k in ['swap','publish','vblank']}
  for pc in markers:cmd(f'break *{pc:#x}')
  # We start paused at swap 1 before executing it. Include its eventual publication.
  while ticks<end:
   reply=cmd('continue');m=re.search(r'Breakpoint \d+, (0x[0-9a-f]+)',reply);assert m,reply[-500:]
   pc=int(m[1],16);assert pc in markers
   cmd('maintenance flush register-cache')
   assert int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)==pc
   kind=markers[pc]
   if kind=='vblank':ticks+=1
   if kind=='swap':
    swaps+=1
    for e in tape['flight_inputs']:
     if e['swap']==swaps:
      if 'key' in e:cmd(f"monitor key {e['key']:x} {e['value']}")
      else:cmd(f"monitor input {e['event']} {e['value']}")
      inputs.append(dict(e,vblank=ticks))
   copper=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a0'))[1],16) if kind=='publish' else None
   events.append(dict(kind=kind,vblank=ticks,swap=swaps,copper=copper))
   if kind=='vblank' and ticks==START:state('start')
   if kind=='vblank' and ticks%50==0:print(out.name,'vblank',ticks,flush=True)
  state('end')
  cpuinfo('end')
  pubs=[e for e in events if e['kind']=='publish' and START<=e['vblank']<end]
  assert pubs
  # One publication per request, unique swap numbers, changing buffers.
  allpubs=[e for e in events if e['kind']=='publish']
  assert len({e['swap'] for e in allpubs})==len(allpubs)
  assert all(a['copper']!=b['copper'] for a,b in zip(allpubs,allpubs[1:]))
  assert all(e['copper']<0x200000 for e in allpubs)
  result=dict(window=[START,end],pal_fields=end-START,publications=len(pubs),pal50_equivalent_fps=50*len(pubs)/(end-START),events=events,inputs=inputs,variant=v)
  (out/'counts.json').write_text(json.dumps(result,indent=2))
  with (out/'frames.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=['frame','swap','vblank','interval','copper']);w.writeheader()
   for i,e in enumerate(pubs):w.writerow(dict(frame=i+1,swap=e['swap'],vblank=e['vblank'],interval='' if i==0 else e['vblank']-pubs[i-1]['vblank'],copper=hex(e['copper'])))
  # Image capture is AFTER the fixed window and cannot affect its timing.
  cmd('delete breakpoints');path=out/'after.trace';cmd(f'monitor profile 1 "" "{path}"')
  t=barto.load(path);(out/('after.png' if t.fields[0].shot_kind else 'after.jpg')).write_bytes(t.fields[0].shot)
  print(out.name,'RESULT',len(pubs),result['pal50_equivalent_fps'],flush=True)
 return capture

def main():
 p=argparse.ArgumentParser();p.add_argument('--machine',choices=['040','020'],required=True);p.add_argument('--variant',choices=VARIANTS,required=True);p.add_argument('--output',required=True);p.add_argument('--seed',required=True);p.add_argument('--extra-args',default='');p.add_argument('--end',type=int,default=END);a=p.parse_args()
 source_text=Path(__file__).read_text()
 os.chdir(ROOT);out=Path(a.output).resolve();v=dict(VARIANTS[a.variant],extra_args=a.extra_args)
 frequencies=re.findall(r'--uae_cpu_frequency=(\d+)',a.extra_args);assert len(frequencies)<=1,'duplicate frequency override'
 v['expected_cpu']=dict(cpu=68040 if a.machine=='040' else 68020,frequency=int(frequencies[0]) if frequencies else (40000000 if a.machine=='040' else 14187580),mmu=0 if a.machine=='020' or '68040-NOMMU' in a.extra_args else 68040,fpu=68040 if a.machine=='040' else 0)
 run(a.machine,out,Path(a.seed).resolve(),observer(v,a.end),v)
 (out/'baseline_matrix.py').write_text(source_text)
 shutil.copy(TAPE,out/'flight.tape.json')
if __name__=='__main__':main()
