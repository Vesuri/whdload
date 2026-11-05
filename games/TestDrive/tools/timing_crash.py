#!/usr/bin/env python3
"""Measure a natural steering crash; native keys only, read-only breakpoints."""
import sys,json,re,shutil
from harness import ROOT,command,server,dump
from race_capture import resolve
from timing_map import decode
out=ROOT/'tmp/phase5'/sys.argv[1]/'crash';out.mkdir(exist_ok=False)
base,rr=resolve(out);h4=rr['h4'];db=rr['td-data']
def cmd(s):
 r=command(s)
 with (out/'actions.jsonl').open('a') as f:f.write(json.dumps(dict(command=s,reply=r))+'\n')
 return r
def hit(off):
 r=server.request('until '+hex(h4+off));(out/f'hit-{off:04x}.txt').write_text(r)
 if f'{h4+off:08x}' not in r.lower():raise RuntimeError(r)
def state(name):
 s=decode(dump(out/(name+'.bin'),db,db+0x32a4).read_bytes());r=cmd('info registers pc a5');fp=int(re.search(r'a5\s+(0x[0-9a-f]+)',r).group(1),16);b=dump(out/(name+'-frame.bin'),fp-52,fp+10).read_bytes()
 for n,o in [('count',-36),('sum',-44)]:s[n]=int.from_bytes(b[52+o:56+o],'big',signed=True)
 (out/(name+'.json')).write_text(json.dumps(s,indent=2)+'\n');return s
try:
 cmd('monitor key 4c 1');cmd('monitor key 40 1');cmd('monitor fields 30');cmd('monitor key 40 0');cmd('monitor fields 150');cmd('monitor key 4e 1')
 hit(0x272);a=state('before-penalty')
 cmd('monitor key 4c 0');cmd('monitor key 4e 0')
 hit(0x32d8);b=state('animation-entry')
 hit(0x2ea);c=state('ack-entry')
 cmd('monitor fields 100');d=state('ack-wait')
 cmd('monitor key 40 1');hit(0xf6);cmd('monitor key 40 0');e=state('recovered')
 result=dict(regions=rr,animation_fields=c['vbl']-b['vbl'],stop_to_ack_fields=c['vbl']-a['vbl'],penalty=b['count']-a['count'],wait_count_change=d['count']-c['count'],wait_speed_sum_change=d['sum']-c['sum'],recovery_count=e['count'],recovery_chances=e['chances'])
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json');print(result)
finally:
 for k in ['4c','4e','40']:cmd('monitor key '+k+' 0')
