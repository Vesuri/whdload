#!/usr/bin/env python3
"""Observe a real grip clamp through debugger-native steering, without guest writes.
Use in an actual player race with C2 enabled, C5 input tape disabled, at speed.
"""
import sys,json,re
from harness import ROOT,server,command,dump
from race_capture import resolve
from check_units import MARK
out=ROOT/'tmp/phase8'/sys.argv[1];out.mkdir(exist_ok=False)
steering_key=0x4f if '--left' in sys.argv[2:] else 0x4e
base,rr=resolve(out);h4=rr['h4'];db=rr['td-data'];a4=db+0x7ffe
listing=ROOT/'tmp/build/verify/TestDrive.lst'
syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',listing.read_text(encoding='latin1'),re.M)}
ram=(out/'code.bin').read_bytes();at=ram.index(MARK)+len(MARK);at=(at+1)&~1;slave=base+at-syms['verify_unit_results']
def read(name,addr,n,signed=True):return int.from_bytes(dump(out/(name+'.bin'),addr,addr+n).read_bytes(),'big',signed=signed)
def hit(off):
 r=server.request('until '+hex(h4+off));(out/f'hit-{off:x}.txt').write_text(r)
 regs=command('info registers pc d0');assert int(re.search(r'pc\s+(0x[0-9a-f]+)',regs)[1],16)==h4+off,r
 return regs
try:
 command(f'monitor key {steering_key:x} 1');hit(0x8172)
 p=read('period',slave+syms['sim_p'],2);assert p in (2,5)
 coarse=read('coarse-clamp',a4-26200,4)
 sign=read('steering-sign',a4-26188,2)
 if '--left' in sys.argv[2:]:assert sign<0,'requested negative clamp was not exercised'
 if sign<0:coarse=-coarse
 grip_carry=read('grip-carry',slave+syms['sim_grip_carry'],2)
 speed_carry=read('speed-carry',slave+syms['sim_speed_carry'],2)
 speed=read('speed-before',a4-22360,4)
 def trunc(x,d):return (1 if x>=0 else -1)*(abs(x)//d)
 expected=coarse if p==5 else trunc(coarse*p+grip_carry,5)
 expected_speed=max(0,speed+trunc(-16384*p+speed_carry,5))
 regs=hit(0x7fba)
 actual=read('fine-clamp',a4-26200,4);after=read('speed-after',a4-22360,4)
 assert actual==expected,(actual,expected)
 assert int(re.search(r'd0\s+(0x[0-9a-f]+)',regs)[1],16)==(expected&0xffffffff),regs
 assert after==expected_speed,(after,expected_speed)
 report=dict(status='PASS',period=p,coarse_clamp=coarse,fine_clamp=actual,grip_carry=grip_carry,speed_before=speed,speed_after=after,scrub_delta=after-speed)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:command(f'monitor key {steering_key:x} 0')
