#!/usr/bin/env python3
"""Read the real stage-results call and rendered text, then acknowledge natively.
Run in an interactive phase-8 session parked near the gas station. No guest
state/register writes: native brake/fire input plus breakpoints and RAM reads.
"""
import argparse,json,re,struct
from harness import ROOT,command,server,dump
from race_capture import resolve
from timing_map import decode
from check_timing import results
p=argparse.ArgumentParser(description=__doc__);p.add_argument('name');a=p.parse_args()
out=ROOT/'tmp/phase8'/a.name;out.mkdir(exist_ok=False)
base,rr=resolve(out);h4=rr['h4'];root=rr['td'];db=rr['td-data']
def cmd(s):
 r=command(s)
 with (out/'actions.jsonl').open('a') as f:f.write(json.dumps(dict(command=s,reply=r))+'\n')
 return r
def registers():
 r=cmd('info registers pc a5 sp')
 return {k:int(re.search(k+r'\s+(0x[0-9a-f]+)',r)[1],16) for k in ['pc','a5','sp']}
def hit(addr):
 r=server.request('until '+hex(addr));(out/f'hit-{addr-root:x}.txt').write_text(r)
 assert registers()['pc']==addr,r
try:
 cmd('monitor key 4c 0');cmd('monitor key 40 0');cmd('monitor key 4d 1')
 hit(h4+0x3a0);cmd('monitor key 4d 0')
 regs=registers();fp=regs['a5'];sp=regs['sp']
 b=dump(out/'race-frame.bin',fp-52,fp+10).read_bytes()
 count=int.from_bytes(b[16:20],'big');total=int.from_bytes(b[8:12],'big')
 state=decode(dump(out/'race-data.bin',db,db+0x32a4).read_bytes())
 args=dump(out/'result-arguments.bin',sp,sp+14).read_bytes()
 actual=dict(car=int.from_bytes(args[:2],'big'),average=int.from_bytes(args[2:6],'big'),seconds=int.from_bytes(args[6:8],'big'),score=int.from_bytes(args[8:12],'big'),reference_seconds=int.from_bytes(args[12:14],'big'))
 expected=results(count,total,state['stage'])
 assert all(actual[k]==v for k,v in expected.items()),(actual,expected)
 assert state['event']==0 and state['gas_approach']==1
 cmd(f'break *{root+0x4448:#x}\nbreak *{root+0x48d6:#x}')
 lines=[]
 for i in range(12):
  cmd('continue');regs=registers()
  if regs['pc']==root+0x48d6:break
  assert regs['pc']==root+0x4448,regs
  ptr=int.from_bytes(dump(out/f'text-pointer-{i}.bin',regs['a5']+8,regs['a5']+12).read_bytes(),'big')
  line=dump(out/f'text-{i}.bin',ptr,ptr+128).read_bytes().split(b'\0')[0].decode('latin1');lines.append(line)
  server.request('shot '+str(out/f'text-{i}.png'))
 else:raise AssertionError('results text loop did not reach acknowledgement')
 cmd('delete')
 assert any('average speed was '+str(actual['average']) in x for x in lines),lines
 assert any(str(actual['score'])+' points.' in x for x in lines),lines
 sec=actual['seconds'];time_text=(f'you {sec//60:2d} minutes and {sec%60:02d} seconds.' if sec>=120 else f'you {sec//60:2d} minute and {sec%60:02d} seconds.' if sec>=60 else f'you {sec:2d} seconds.')
 assert time_text in lines,(time_text,lines)
 server.request('shot '+str(out/'station.png'))
 cmd('monitor key 40 1');hit(h4+0xf6);cmd('monitor key 40 0')
 end=decode(dump(out/'next-stage.bin',db,db+0x32a4).read_bytes())
 assert end['stage']==state['stage']+1 and end['score_total']==state['score_total']
 report=dict(status='PASS',stage=state['stage'],next_stage=end['stage'],count=count,speed_sum=total,expected=expected,actual=actual,rendered_lines=lines,score_total=end['score_total'])
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
 cmd('monitor key 4d 0');cmd('monitor key 40 0');cmd('delete')
