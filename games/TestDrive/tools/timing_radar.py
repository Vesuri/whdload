#!/usr/bin/env python3
"""Brake during natural pursuit; sample the script without acknowledgement input."""
import sys,json,re,shutil
from harness import ROOT,command,server,snapshot
from race_capture import resolve
from timing_samples import capture
out=ROOT/'tmp/phase5'/sys.argv[1]/'radar';out.mkdir(exist_ok=False)
base,rr=resolve(out);server.request('until '+hex(rr['h4']+0xfc));r=command('info registers pc a5');(out/'anchor.txt').write_text(r);fp=int(re.search(r'a5\s+(0x[0-9a-f]+)',r).group(1),16)
try:
 (out/'input.txt').write_text(command('monitor key 4d 1'))
 capture(1501,out/'states',rr,fp)
finally:command('monitor key 4d 0')
snapshot(out/'end');shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json')
s=json.loads((out/'states/samples.json').read_text());changes={}
for n in ['police_clock','police_stop','police_phase','event','chances']:
 changes[n]=[(i,x[n]) for i,x in enumerate(s) if i==0 or x[n]!=s[i-1][n]]
print(json.dumps(changes));(out/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
