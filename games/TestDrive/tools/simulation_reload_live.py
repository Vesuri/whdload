#!/usr/bin/env python3
"""Native restart from a live C2/C3 session; observe h4 unload and repatching."""
import sys,json,re,shutil
from harness import ROOT,server,command,dump,sha,live_regions
from race_capture import resolve
from check_units import MARK
from check_disabled import check
import native_input as n
out=ROOT/'tmp/phase8'/sys.argv[1];session=ROOT/'tmp/phase8'/sys.argv[2];out.mkdir(exist_ok=False);n.LOG=out/'native-actions.jsonl'
for name in ['slave.slave','slave.lst','machine.json']:shutil.copyfile(session/name,out/name)
base,rr=resolve(out/'before');raw=(out/'before/code.bin').read_bytes()
syms={k:int(a,16) for k,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
at=raw.index(MARK)+len(MARK);at=(at+1)&~1;slave=base+at-syms['verify_unit_results']
try:
 n.key(0x63,True);n.key(0x13,True)
 for i in range(4):
  reply=n.request('until '+hex(slave+syms['overlay_unload_end']))
  (out/f'unload-{i}.txt').write_text(reply)
  n.key(0x13,False);n.key(0x63,False)
  stub=dump(out/f'unloaded-stub-{i}.bin',rr['td-data']+668,rr['td-data']+676).read_bytes()
  if stub[:2]==bytes.fromhex('6100'):break
 else:raise AssertionError('h4 unload not observed')
 n.fields(700);n.request('shot '+str(out/'restart-menu.png'))
 n.key(0x40,True);reply=n.request('until '+hex(slave+syms['verify_race_entry']));(out/'reentry.txt').write_text(reply);n.key(0x40,False)
 base,rr=live_regions(out);raw=(out/'code.bin').read_bytes();stub=rr['td-data']-base+668
 assert raw[stub:stub+2]==bytes.fromhex('4ef9')
 rr['h4']=int.from_bytes(raw[stub+2:stub+6],'big')
 assert (out/'chip.bin').read_bytes()[rr['h4']:rr['h4']+4]==bytes.fromhex('4e55ffcc')
 (out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,options=dict(C1=0,C2=1,C3=1,C4=0,C5=0),slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
 report=check(out);(out/'byte-check.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status='PASS',unload_observed=True,reentry_observed=True,checked_declarations=len(report['ranges']))),flush=True)
finally:
 for key in [0x13,0x63,0x40]:n.key(key,False)
