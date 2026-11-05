#!/usr/bin/env python3
"""Matched renderer self-cycle samples; explicitly report the old 3% threshold."""
import json,re
from pathlib import Path
from subunit_cost import measure
from amigaxdev import barto
from harness import ROOT
reports={}
for name in ['cost-previous','cost-long']:
 p=ROOT/'tmp/corner-jump'/name;result=measure(p,100);result["limit"]=3
 m=json.loads((p/'capture.json').read_text());b=(p/'code.bin').read_bytes();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
 off=m['regions']['td']+0x6390-m['base'];base=int.from_bytes(b[off+2:off+6],'big')-syms['overlay_unload_end'];lo=base+syms['render_overlay_loaded'];hi=base+syms['render_subunit_end'];prev=None;ratio=False;bank=False;extra=bank_sine=0
 trace=barto.load(p/'trace.bin')
 for field in trace.fields:
  for pc,cycles,regs in trace.instructions(field):
   if pc==base+syms['sim_ratio'] and prev is not None and lo<=prev<hi:ratio=True
   if pc is not None and lo<=pc<hi:ratio=False
   if ratio:extra+=cycles
   if 'render_curve_seed' in syms and pc==base+syms['render_curve_seed']:bank=True
   if pc==m['regions']['h4']+0x1b2a:bank=False
   if bank and pc is not None and m['regions']['td']+0x2108<=pc<=m['regions']['td']+0x2144:bank_sine+=cycles
   if pc is not None:prev=pc
 result.update(shared_lane_helper_cycles=extra,additional_bank_sine_cycles=bank_sine)
 result['total_patch_percent']=100*(result['self_cycles']+extra+bank_sine)/result['total_cycles']
 result['legacy_3_percent_gate_passed']=result['total_patch_percent']<3
 reports[name]=result
reports['increment_percentage_points']=reports['cost-long']['total_patch_percent']-reports['cost-previous']['total_patch_percent']
reports['status']='MEASURED: correctness-fix performance exception; previous 3% threshold not met'
reports['scope']='Matched 100-field PAL A500 moving-demo samples (monitor capped the requested 200); hook/displaced self cycles and shared lane helper, plus new bank sine callee; both arms rendered nine main views. Not a whole-race bound.'
(ROOT/'tmp/corner-jump/cost-comparison.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
