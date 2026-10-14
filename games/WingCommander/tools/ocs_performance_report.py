#!/usr/bin/env python3
"""E1 field-bounded throughput, complete-call cost and memory evidence.
Overloads remain measurements; this report never relaxes the D3 cadence gate.
"""
import argparse,json,hashlib
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from ocs_baseline_report import parse,distribution
from ocs_reconstruct import new_output,require

NATIVE={0x2be:'world',0x290fa:'geometry',0x27cfa:'debris',0x281c0:'flames',
 0x2837a:'attachments',0x9618:'asteroids',0x2ba2c:'sort',0x2bab4:'raster',
 0x3260a:'conversion_submit',0xb80:'finish',0x2bf8e:'composition',0x2adb6:'multiply',0x2b6bc:'hypotenuse',0x2b950:'radius',
 0x2abfa:'transform',0x15700:'collision_scan_body'}
OWNED=('intro_world','intro_draw','intro_finish','ocs_prediction_input','ocs_clock_tick',
       'ocs_clock_draw','ocs_prediction_field','ocs_input_record')

def profile(root,build,name):
 m=json.loads((root/'result.json').read_text());b=json.loads((build/'build.json').read_text())
 require(m['effective']['cpu_model']=='68000','instruction cycle denominator only validated for stock 68000')
 h=m['hunks'][0];base=m['slave'];sy=b['symbols']
 game=(root/'simulator-h0.bin').read_bytes();payload=(build/'WingCommander.Slave').read_bytes()[32:-4]
 scopes={h+o:n for o,n in NATIVE.items() if n!='collision_scan_body'}
 scopes.update({base+sy[n]:n for n in OWNED})
 t=barto.load(str(root/name));active={};values={n:[] for n in scopes.values()};total=0;pc_cost={}
 for field in t.fields:
  for pc,cy,regs in t.instructions(field):
   total+=cy
   if pc is not None:pc_cost[pc]=pc_cost.get(pc,0)+cy
   if pc in scopes and scopes[pc] not in active:active[scopes[pc]]=[regs[15],0]
   for x in active.values():x[1]+=cy
   raw=game[pc-h:pc-h+2] if pc is not None and h<=pc<h+len(game) else payload[pc-base:pc-base+2] if pc is not None and base<=pc<base+len(payload) else b''
   if raw==b'\x4e\x75':
    for key in [key for key,x in active.items() if x[0]==regs[15]]:
     values[key].append(active.pop(key)[1]/7093790*1000)
 # The trace is independent of the field event observer. Entire fields must
 # account for their calibrated CPU clocks, even if a complete scope is absent.
 require(all(f.cycles==227*313*2 for f in t.fields),'unexpected trace field geometry')
 elapsed=sum(f.cycles for f in t.fields)/7093790
 require(abs(total/7093790-elapsed)<.0001,'trace cycle accounting')
 return dict(fields=len(t.fields),accounted_ms=total/7093.79,
   inclusive_ms={n:distribution(v) if v else None for n,v in values.items()},
   boundary_scopes_excluded=list(active),
   scope='complete entry/RTS with matching SP; includes callees/interrupts; never sum nested scopes')

def window(root,build,label):
 b=json.loads((build/'build.json').read_text());m=json.loads((root/'result.json').read_text());sy=b['symbols']
 require(m['slave_sha256']==b['sha256']==hashlib.sha256((build/'WingCommander.Slave').read_bytes()).hexdigest(),'wrong build')
 rows=parse(root/(label+'-events.txt'));begin=rows[0];end=next(r for r in rows if r[0]=='E')
 n=250 if label=='asteroids' else m['fire_fields'];fields=[r for r in rows if r[0]=='F']
 require(len(fields)==n and fields[-1][1]==end[1],'unfrozen or incomplete window')
 require(begin[2:5]==[28375160,512,256 if m['effective']['cpu_model']=='68000' else 128],'uncalibrated clock')
 hz=begin[2]/8*begin[3];seconds=(end[1]-begin[1])/hz
 times=[begin[1]]+[r[1] for r in fields]
 require(set(z-a for a,z in zip(times,times[1:]))<={227*312*512,227*313*512},'field clock')
 ticks=[r for r in rows if r[0]=='P' and r[2]==0x2dc]
 require(len(ticks)==((fields[-1][3]-begin[5])&65535),'world counter disagreement')
 dma=[r for r in rows if r[0]=='D'];require(len(dma)==n,'DMA coverage')
 flips=[z for a,z in zip(dma,dma[1:]) if a[3]!=z[3]]
 def intervals(items):
  v=[(z[1]-a[1])/hz*1000 for a,z in zip(items,items[1:])]
  return distribution(v) if v else None
 raw=(root/(label+'-fast.bin')).read_bytes();base=m['slave']-0x200000
 def get(name,size=4):return int.from_bytes(raw[base+sy[name]:base+sy[name]+size],'big')
 require(get('intro_active' if label=='asteroids' else 'ocs_clock_active',2)==1,'window crossed scene exit')
 require(get('ocs_input_overflows')==get('ocs_input_missing')==0,'input loss')
 return dict(seconds=seconds,world_ticks=len(ticks),world_hz=len(ticks)/seconds,
   within_one_tick_target=abs(len(ticks)-n/5)<=1,displayed_pictures=len(flips),displayed_hz=len(flips)/seconds,
   display_intervals_ms=intervals(flips),world_intervals_ms=intervals(ticks),
   maximum_flight_backlog_fields=get('ocs_clock_backlog_max'),input_overflows=get('ocs_input_overflows'),
   missing_samples=get('ocs_input_missing'),prediction_enabled=get('ocs_prediction_fast',2))

def memory(root):
 samples=[]
 m=json.loads((root/'result.json').read_text())
 for label in m['checkpoints']:
  chip=(root/(label+'-chip.bin')).read_bytes();fast=(root/(label+'-fast.bin')).read_bytes()
  def get(address,size=4):
   if 0<=address<=len(chip)-size:raw=chip[address:address+size]
   else:
    offset=address-0x200000
    require(0<=offset<=len(fast)-size,'memory header outside physical RAM')
    raw=fast[offset:offset+size]
   return int.from_bytes(raw,'big')
  header=get(get(4)+322);free_chip=free_fast=0
  for _ in range(16):
   following=get(header)
   if not following:break
   attrs=get(header+14,2);lo=get(header+20);hi=get(header+24);free=get(header+28)
   require(lo<hi and free<=hi-lo,'invalid memory header')
   if attrs&2:
    require(hi<=0x80000,'unexpected Chip bank');free_chip+=free
   if attrs&4:
    require(0x200000<=lo<hi<=0x600000,'not physical Fast');free_fast+=free
   header=following
  else:raise ValueError('unterminated memory list')
  samples.append(dict(checkpoint=label,chip_used=len(chip)-free_chip,fast_used=len(fast)-free_fast))
 return dict(samples=samples,maximum_sampled_chip_used=max(x['chip_used'] for x in samples),
             maximum_sampled_fast_used=max(x['fast_used'] for x in samples),scope='OS pool snapshots, not boot-wide peaks')

def report(root,build):
 m=json.loads((root/'result.json').read_text());b=json.loads((build/'build.json').read_text())
 r=dict(build_sha256=b['sha256'],emulator_sha256=m['fsuae_sha256'],machine=m['effective'],
  input=m['flight_input'],windows={n:window(root,build,n) for n in ('asteroids','fire')},
  memory=dict(slave_bytes=b['bytes'],extra_vs_d4_bytes=b['bytes']-39784,history_bytes=b['history_bytes'],
   allocation_policy=b['workspace'],chip_kib=512,fast_kib=4096,usage=memory(root)),profiles={})
 if m['effective']['cpu_model']=='68000':
  for name in ('intro-cost.bin','prediction-cost.bin','fire-cost.bin'):
   if (root/name).exists():r['profiles'][name]=profile(root,build,name)
 return r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',required=True);a=p.parse_args()
 r=report(a.run,a.build);out=new_output(a.output);out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
