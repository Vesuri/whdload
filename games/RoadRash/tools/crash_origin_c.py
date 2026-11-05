"""Break immediately before the first player crash-state write in a known lap window."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text());start=int(os.environ.get('RR_CRASH_START','1300'))
 for target,event,value in tape['events']:
  if target>start:break
  advance(s,target);s.input(event,value)
 advance(s,start)
 assert read_bytes(s,0xa5dce,1)==b'\xff','player already crashed before requested window'
 copy=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 native=[0x8c07a,0x8c29e,0x8c6de,0x8c75a,0x8cf88,0x8e3b0,0x8e4b8,0x8e640,0x8e6b0,0x8e8a6,0x8e8c2,0x8e982,0x8ee6c]
 mapping={copy+a-0x8b486 if 0x8b486<=a<0x8d006 else a:a for a in native}
 for i,pc in enumerate(mapping,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} $a1 == 0xa5d60 && *(signed char*)0xa5dce < 0')
 s.cmd('continue',timeout=60)
 regs=s.cmd('info registers');pc=int(re.search(r'\bpc\s+0x([0-9a-fA-F]+)',regs)[1],16);assert pc in mapping
 result=dict(start=start,native_pc=hex(mapping[pc]),actual_pc=hex(pc),registers=regs,snapshot=snapshot(s),cursor=rd(s,0xa5d50),player=read_bytes(s,0xa5d60,128).hex(),actors=read_bytes(s,0xa5d60,0x1180).hex(),stack=s.cmd('x/12wx $sp'),provenance=provenance(os.environ['SLAVE'],s))
 a0=int(re.search(r'\ba0\s+0x([0-9a-fA-F]+)',regs)[1],16)
 result['object_address']=hex(a0)
 result['object_record']=read_bytes(s,a0,20).hex()
 result['object_distances']=read_bytes(s,0xa5a04,0x100).hex()
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('crash origin',result['native_pc'],'live',result['snapshot']['field'],'cursor',result['cursor'],flush=True)
finally:s.quit()
