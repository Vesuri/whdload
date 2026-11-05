import sys,json,struct,hashlib
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 initial=route(s);s.input('JOY2_UP',1);main=rd(s,0x87480);head=read_bytes(s,main,4);assert head[:2]==bytes.fromhex('6100')
 target=main+2+struct.unpack_from('>h',head,2)[0];code=read_bytes(s,target,256);off=code.find(b'RRACTOR1');assert off>=0;actor_stats=target+off
 data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0;end=rd(s,0x875b8);code=read_bytes(s,end,main+off-end);rts=code.rfind(bytes.fromhex('4e75'));assert rts>=0 and len(code)-rts<=4
 s.cmd(f'break *{end+rts:#x}')
 while True:
  s.cmd('continue',timeout=60);cursor=rd(s,0xa5d50);state,base,count,allocation=struct.unpack('>4I',read_bytes(s,actor_stats+8,16));assert state==3
  actors=read_bytes(s,base,0x1180);others=b''.join(read_bytes(s,a,n) for a,n in [(0xa5d50,16),(0xa5d1e,4),(0xa5d22,4),(0xa7220,8),(0xa59f4,2)])
  rows.append(dict(cursor=cursor,actor_hash=hashlib.sha256(actors).hexdigest(),other_hash=hashlib.sha256(others).hexdigest(),position=int.from_bytes(actors[4:8],'big')))
  if cursor>=600:break
  assert len(rows)<600
 (s.out/'actors.bin').write_bytes(actors);(s.out/'replay.json').write_text(json.dumps(dict(initial=initial,rows=rows,base=hex(base),provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('recorded',len(rows),'completed ticks',rows[0]['cursor'],rows[-1]['cursor'],flush=True)
finally:s.quit()
