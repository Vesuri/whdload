#!/usr/bin/env python3
"""Validate a read-only frame counter against instruction and display-DMA evidence."""
import argparse,json,struct,sys,csv
from pathlib import Path
from tfx import server
from amigaxdev import barto
from replay_flight import sha

# Frozen before comparison: neutral flight, game vblank +2 inclusive to +18 exclusive.
START,END=2,18

def check(observed,traced):
 o=json.loads((observed/'counts.json').read_text());t=json.loads((traced/'counts.json').read_text())
 assert o['mode']=='observe' and t['mode']=='trace'
 for name in ['slave_sha256','fpsp040_sha256','fpsp060_sha256','tape_sha256','seed_sha256']:
  assert json.loads((observed/'manifest.json').read_text())[name]==json.loads((traced/'manifest.json').read_text())[name],name
 assert t['trace_sha256']==sha(traced/'full.trace')
 def window(r):
  return [{'kind':e['kind'],'vblank':e['clock']-r['initial_clock'],'copper':e['copper']} for e in r['events'] if START<=e['clock']-r['initial_clock']<END]
 a,b=window(o),window(t)
 assert a==b,('counter/trace mismatch',a,b)
 assert sum(e['kind']=='vblank' for e in a)==END-START
 assert len([e for e in a if e['kind']=='publish'])>=4
 # Publication must alternate the two lists, with one preceding swap request each.
 pending=None;previous=None;rows=[]
 for e in a:
  if e['kind']=='swap':
   assert pending is None,'two requests without publication';pending=e
  elif e['kind']=='publish':
   assert pending is not None,'publication without request'
   assert previous!=e['copper'],'same buffer republished'
   rows.append(dict(frame=len(rows)+1,swap_vblank=pending['vblank'],publication_vblank=e['vblank'],vblanks_since_previous=None if not rows else e['vblank']-rows[-1]['publication_vblank'],copper=hex(e['copper'])))
   pending=None;previous=e['copper']
 assert pending is None
 trace=barto.load(traced/'full.trace')
 # All 8 plane pointers in each copper list; assert next-field bitplane DMA uses them.
 dma_checks=[]
 for e in t['events']:
  if e['kind']!='publish' or not START<=e['clock']-t['initial_clock']<END:continue
  words={}
  for off in range(e['copper'],e['copper']+192,4):
   reg,val=struct.unpack_from('>HH',trace.chip,off)
   if 0xe0<=reg<=0xfe:words[reg]=val
  planes=[(words[0xe0+4*i]<<16)|words[0xe2+4*i] for i in range(8)]
  f=trace.fields[e['field']+1];first={}
  assert f.dma_size==58,f.dma_size
  for off in range(0,len(f.dma),f.dma_size):
   if struct.unpack_from('<h',f.dma,off+29)[0]==6:
    reg=struct.unpack_from('<H',f.dma,off)[0]
    first.setdefault(reg,struct.unpack_from('<I',f.dma,off+12)[0])
  actual=[first[0x110+2*i] for i in range(8)]
  assert actual==planes,(e,actual,planes)
  dma_checks.append({'vblank':e['clock']-t['initial_clock'],'field':f.index,'copper':hex(e['copper']),'plane_addresses':list(map(hex,planes))})
 assert len(dma_checks)==len(rows)
 return {'passed':True,'window':{'start_vblank_inclusive':START,'end_vblank_exclusive':END},'publications':len(rows),'vblanks':END-START,'instruction_records_in_capture':t['instruction_records'],'frames':rows,'dma_checks':dma_checks,'events':a}

def main():
 p=argparse.ArgumentParser();p.add_argument('observe',type=Path);p.add_argument('trace',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=check(a.observe,a.trace);a.output.write_text(json.dumps(r,indent=2))
 with a.output.with_suffix('.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(r['frames'][0]));w.writeheader();w.writerows(r['frames'])
 print(json.dumps({k:v for k,v in r.items() if k not in ['frames','dma_checks','events']},indent=2))
if __name__=='__main__':main()
