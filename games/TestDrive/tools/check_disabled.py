#!/usr/bin/env python3
"""Check installed optional game ranges against original bytes or selected helpers.
"""
import argparse,json,re,struct
from pathlib import Path
from audit_simulation import ranges,originals,gate_on
from harness import ROOT,sha
from check_units import MARK

def check(p,chip_override=None):
 meta=json.loads((p/'capture.json').read_text());opts=meta['options'];ram=(p/'code.bin').read_bytes();chip=(p/'chip.bin').read_bytes() if chip_override is None else chip_override
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
 # The always-on unload hook identifies the executing slave in either build.
 hook=meta['regions']['td']+0x6390-meta['base']
 assert ram[hook:hook+2]==bytes.fromhex('4ef9'),'missing overlay unload jump'
 slave=int.from_bytes(ram[hook+2:hook+6],'big')-syms['overlay_unload_end']
 if MARK in ram:
  at=ram.index(MARK)+len(MARK);at=(at+1)&~1
  assert slave==meta['base']+at-syms['verify_unit_results'],'inconsistent slave resolution'
 else:
  assert not any(opts[k] for k in ['C1','C3','C4','C5']),'normal build has no VERIFY options'
 bs=originals();checked=[]
 for r in ranges():
  h,a,n,g=r['hunk'],r['offset'],r['size'],r['gate'];addr=meta['regions']['td' if h=='root' else h]+a
  if meta['base']<=addr<meta['base']+len(ram):actual=ram[addr-meta['base']:addr-meta['base']+n]
  else:actual=chip[addr:addr+n]
  enabled=gate_on(g,opts)
  if not enabled and any((q['hunk'],q['offset'],q['size'])==(h,a,n) and gate_on(q['gate'],opts) for q in ranges()):continue
  if not enabled:expected=bs[h][a:a+n]
  elif r['label']=='current_x':expected=bytes.fromhex('946ca898')
  elif r['label']=='nop':expected=bytes.fromhex('4e71')*(n//2)
  elif r['label']=='fixed_seed':expected=bytes.fromhex('397c12349bd84e71')
  elif r['label']=='beam_removed':expected=bytes.fromhex('42404e714e71')
  else:expected=bytes.fromhex('4ef9' if r['label'] in ['audio_start','render_finish','render_lateral_forward_step','render_lateral_rear_step','render_slope_add','render_height_fraction','render_slope_begin','render_curve_seed'] else '4eb9')+struct.pack('>I',slave+syms[r['label']])+bytes.fromhex('4e71')*((n-6)//2)
  assert actual==expected,(h,hex(a),g,actual.hex(),expected.hex())
  checked.append(dict(hunk=h,offset=a,enabled=enabled))
 return dict(status='PASS',ranges=checked,captured_slave=sha(p/'slave.slave'))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);a=p.parse_args();print(json.dumps(check(a.capture),indent=2))
