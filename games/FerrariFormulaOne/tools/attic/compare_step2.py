#!/usr/bin/env python3
"""Compare completed-update semantic blocks, with narrow proven pointer normalization.
Opaque gameplay blocks are retained: do not omit a byte merely because it varies.
"""
from pathlib import Path
import json,struct,hashlib
root=Path(__file__).resolve().parents[1]
FIELDS=[('demo_mode',0x1bee8,2),('boost',0x1bf52,2),('control_mode',0x1c1c2,2),('difficulty',0x1c1c4,2),('steering_all_cars',0x1c6a2,16),('condition_block_22356',0x22356,32),('race_status_all_cars',0x2268e,32),('clocks',0x226c0,20),('speed_all_cars',0x2275a,16),('car_progress_state',0x2276a,96),('rng',0x24f60,120),('gear_and_condition',0x66c3c,60),('segments_and_positions',0x6a60a,96),('headings',0x6a66a,32),('race_extended_state',0x6ef20,0x372)]
def state(b):
 out={name:bytearray(b[lo:lo+size]) for name,lo,size in FIELDS}
 # Exactly two pointer words, statically proven to address the 56-word RNG table.
 for at in (112,116):
  ptr=struct.unpack_from('>I',out['rng'],at)[0];assert 0x24f60<=ptr<0x24fd0 and ptr%2==0
  struct.pack_into('>I',out['rng'],at,ptr-0x24f60)
 return {k:bytes(v) for k,v in out.items()}
def compare(a,b):return [k for k in a if a[k]!=b[k]]
def main():
 d=root/'tmp/step2';a=(d/'verified-demo-a/anchor.bin').read_bytes();b=(d/'verified-demo-b/anchor.bin').read_bytes();slow=(d/'slow-demo/anchor.bin').read_bytes();scene=(d/'verified-demo-a/after-display.bin').read_bytes()
 poison=bytearray(a);poison[0x2275b]^=1
 results={'two_fresh_boots_all_chip_equal':a==b,'repeat_mismatches':compare(state(a),state(b)),'slow_drawing_mismatches':compare(state(a),state(slow)),'later_demo_mismatches':compare(state(a),state(scene)),'deliberate_speed_byte_mismatches':compare(state(a),state(poison))}
 assert results['two_fresh_boots_all_chip_equal'] and not results['repeat_mismatches']
 assert not results['slow_drawing_mismatches']
 assert results['later_demo_mismatches'] and results['deliberate_speed_byte_mismatches']==['speed_all_cars']
 (root/'manifest/step2-state-checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
