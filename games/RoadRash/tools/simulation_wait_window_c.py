import os,sys,json,re,struct
from harness_a import *
s=Session(sys.argv[1]);events=[]
try:
 route(s);s.input('JOY2_UP',1);advance(s,300)
 main=rd(s,0x87480);data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0;stats=main+off
 end=rd(s,0x875b8);code=read_bytes(s,end,stats-end);off=code.rfind(bytes.fromhex('4e75'));assert off>=0 and len(code)-off<=4;ret=end+off
 sites={main:'step_main',ret:'step_completed',0x875c8:'render_begin',0x87736:'wait_begin',0x8773c:'wait_end',0x871dc:'publish'}
 for a in sites:s.cmd(f'break *{a:#x}')
 for i in range(180):
  s.cmd('continue',timeout=60);pc=int(re.search(r'pc\s+0x([0-9a-f]+)',s.cmd('info registers pc'))[1],16)
  raw=read_bytes(s,0xdff004,4);v=struct.unpack('>I',raw)[0];beam=((v>>16)&1)*256+((v>>8)&255)
  events.append(dict(site=sites[pc],pc=hex(pc),field=field(s),cursor=rd(s,stats+8),beam=beam,beam_raw=raw.hex(),soft=read_bytes(s,0xaec0c,1)[0],position=rd(s,0xa5d64)))
 (s.out/'windows.json').write_text(json.dumps(dict(events=events,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('events',len(events),flush=True)
finally:s.quit()
