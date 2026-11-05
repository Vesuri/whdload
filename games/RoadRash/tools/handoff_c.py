import os,sys,json,re
from harness_a import *
s=Session(sys.argv[1]);events=[]
try:
 route(s);s.input('JOY2_UP',1);advance(s,300)
 for a in [0x875c8,0x87736,0x8773c,0x871dc,0x8713a]:s.cmd(f'break *{a:#x}')
 for i in range(40):
  s.cmd('continue',timeout=60)
  pc=int(re.search(r'pc\s+0x([0-9a-f]+)',s.cmd('info registers pc')).group(1),16)
  producer=rd(s,0xa7266);consumer=rd(s,0xa726a)
  e=dict(pc=hex(pc),field=field(s),soft=read_bytes(s,0xaec0c,1)[0],beam=read_bytes(s,0xdff004,4).hex(),producer=hex(producer),consumer=hex(consumer),ready=[rd(s,0xa7238,2),rd(s,0xa723a,2)],drains=[rd(s,0xa7bee,2),rd(s,0xa7bf0,2)],front=hex(rd(s,0x404)),back=hex(rd(s,0x408)))
  events.append(e)
 (s.out/'handoff.json').write_text(json.dumps(dict(events=events,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
 for e in events[:12]:print(e)
finally:s.quit()
