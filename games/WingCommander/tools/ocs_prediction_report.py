#!/usr/bin/env python3
"""D3 native-model cost, authoritative equality and publication-lead evidence."""
import argparse,json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from ocs_baseline_report import parse,distribution
from ocs_clock_report import equal
from ocs_reconstruct import new_output,require

SCOPES=('ocs_input_record','ocs_prediction_field','ocs_clock_tick',
        'ocs_prediction_begin','ocs_prediction_end','ocs_clock_draw')

def costs(root,build):
 b=json.loads((build/'build.json').read_text());sy=b['symbols'];m=json.loads((root/'result.json').read_text())
 require(m['slave_sha256']==b['sha256'],'wrong cost build')
 require(m['effective']['cpu_model']=='68000','cost denominator is stock A500 only')
 base=m['slave'];payload=(build/'WingCommander.Slave').read_bytes()[32:-4]
 trace=barto.load(str(root/'prediction-cost.bin'))
 require(len(trace.fields)==10,'bounded ten-field trace required')
 records=[r for f in trace.fields for r in trace.instructions(f)]
 require(sum(pc==base+sy['ocs_input_record'] for pc,_,_ in records)==10,'missing full input producer coverage')
 measured={}
 for name in SCOPES:
  active=None;values=[]
  for pc,cost,regs in records:
   if pc==base+sy[name] and active is None:active=[regs[15],0]
   if active:
    active[1]+=cost
    # Complete owned entry/RTS scopes only. Tail-dispatched routines are not
    # attributed this way; samples crossing trace boundaries are excluded.
    if pc is not None and base<=pc<base+len(payload) and payload[pc-base:pc-base+2]==bytes.fromhex('4e75') and regs[15]==active[0]:
     values.append(active[1]/7093790*1000);active=None
  measured[name]=distribution(values) if values else None
 return dict(inclusive_ms=measured,fields=10,scope='Barto complete owned calls, native callees/interrupts included; boundary calls excluded')

def window(root,build):
 b=json.loads((build/'build.json').read_text());sy=b['symbols'];m=json.loads((root/'result.json').read_text())
 rows=parse(root/'fire-events.txt');begin=next(r for r in rows if r[0]=='B');end=next(r for r in rows if r[0]=='E')
 fields=[r for r in rows if r[0]=='F'];n=m['fire_fields'];require(len(fields)==n,'incomplete field window')
 hz=begin[2]/8*begin[3];seconds=(end[1]-begin[1])/hz
 require(begin[2:5]==[28375160,512,256 if m['effective']['cpu_model']=='68000' else 128],'uncalibrated emulated denominator')
 times=[r[1] for r in fields];require(set(y-x for x,y in zip([begin[1]]+times[:-1],times))<={227*312*512,227*313*512},'field timing')
 raw=(root/'fire-fast.bin').read_bytes();base=m['slave']-0x200000
 def get(name,size=4):return int.from_bytes(raw[base+sy[name]:base+sy[name]+size],'big')
 require(get('ocs_clock_active',2)==1,'flight window crossed a modal exit')
 require(get('ocs_input_overflows')==get('ocs_input_missing')==0,'input history loss')
 ticks=[r for r in rows if r[0]=='P' and r[2]==0x2dc]
 require(len(ticks)==((fields[-1][3]-begin[5])&65535),'world counter disagreement')
 require(abs(len(ticks)-n/5)<=1,'normal-load completed cadence outside one-tick boundary tolerance')
 dma=[r for r in rows if r[0]=='D'];flips=sum(a[3]!=z[3] for a,z in zip(dma,dma[1:]))
 forecasts=[r for r in rows if r[0]=='G'];require(forecasts,'actual queue-target observer required')
 predicted=[]
 for _,clock,estimate,target,ready,enabled in forecasts:
  def delta(a,z):return ((a-z+0x80000000)&0xffffffff)-0x80000000
  require(target==(estimate if enabled and delta(estimate,ready)>0 else ready),'wrong asynchronous deadline')
  if enabled:predicted.append(max(0,delta(target,estimate)))
 return dict(input=m.get('flight_input','held fire'),seconds=seconds,completed_ticks=len(ticks),world_hz=len(ticks)/seconds,
  displayed_pictures=flips,displayed_hz=flips/seconds,maximum_backlog_fields=get('ocs_clock_backlog_max'),
  input_overflows=get('ocs_input_overflows'),missing_samples=get('ocs_input_missing'),
  measured_service_fields=get('ocs_prediction_cost'),predicting=get('ocs_prediction_fast',2),
  zero_acceleration_cache_hits=get('ocs_acceleration_hits'),
  predicted_queues=len(predicted),late_forecast_fields=predicted)

def compare(on,off):
 metas=[json.loads((p/'result.json').read_text()) for p in (on,off)]
 for key in ('slave_sha256','fsuae_sha256','effective','hunks','slave','a4'):
  require(metas[0][key]==metas[1][key],'unmatched prediction control '+key)
 modes=[json.loads((p/'clock-samples.json').read_text())['prediction_mode'] for p in (on,off)]
 require(modes==['on','off'],'missing on/off control')
 for tick in (41,51):equal(*[(p/f'tick{tick}-data.bin').read_bytes() for p in (on,off)])
 data=bytearray((on/'tick51-data.bin').read_bytes());data[0x8928]^=1
 try:equal(data,(off/'tick51-data.bin').read_bytes())
 except ValueError:pass
 else:raise ValueError('corrupt pose survived')
 return dict(equal_ticks=[41,51],rejected=['corrupted authoritative position'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--build',type=Path,required=True)
 p.add_argument('--compare-off',type=Path);p.add_argument('--output',required=True);a=p.parse_args()
 result=dict(passed=True,window=window(a.run,a.build))
 if json.loads((a.run/'result.json').read_text())['effective']['cpu_model']=='68000':result['costs']=costs(a.run,a.build)
 if a.compare_off:result['comparison']=compare(a.run,a.compare_off)
 out=new_output(a.output);out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
