import sys,json,re,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[];actions=[];render=False;stage=0
try:
 route(s)
 horizon_addr=None
 if os.environ.get('RR_MEASURED'):
  target=rd(s,0x8773e);code=read_bytes(s,target,80);idx=code.find(bytes.fromhex('41fa'));assert idx>=0
  horizon_addr=target+idx+2+struct.unpack_from('>h',code,idx+2)[0]
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-sym('step_main');history=base+sym('step_pose_headings')
 s.input('JOY2_UP',1);advance(s,300);s.input('JOY2_RIGHT',1)
 for pc in (0x875c8,0x87736,0x8a8ec):s.cmd(f'break *{pc:#x}')
 for _ in range(3000):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers pc a1 d1')
  reg=lambda key:int(re.search(key+r'\s+0x([0-9a-f]+)',regs)[1],16)
  pc=reg('pc');f=field(s)
  if stage==0 and f>=310:s.input('JOY2_RIGHT',0);stage=1;actions.append([f,'release'])
  if stage==1 and f>=320:s.input('JOY2_LEFT',1);stage=2;actions.append([f,'reverse'])
  if pc==0x875c8:render=True
  elif pc==0x87736:render=False
  elif reg('a1')==0xa5d60:
   heading=struct.unpack('>h',read_bytes(s,0xa5d6c,2))[0];predicted=reg('d1')&65535;predicted=predicted-65536 if predicted&32768 else predicted
   raw=read_bytes(s,0xa598c,1)[0]&12
   horizon=rd(s,horizon_addr,2) if horizon_addr is not None else None
   if horizon is not None:assert 0<=horizon<=4,horizon
   age=max(0,rd(s,horizon_addr-4)-rd(s,0xa5d50))
   effective=min(4,age+horizon)
   slope=struct.unpack('>h',read_bytes(s,history+8,2))[0]
   expected=heading
   if render and ((slope>0 and raw==8 and heading>=0) or (slope<0 and raw==4 and heading<0)):
    expected+=slope*effective>>2
   assert predicted==expected,(heading,predicted,expected,age,effective,slope,render,raw)
   rows.append(dict(age=age,effective=effective,slope=slope,horizon=horizon,field=f,cursor=rd(s,0xa5d50),render=render,heading=heading,predicted=predicted,raw=raw))
   if not render or raw not in (4,8) or (raw==4 and heading>=0) or (raw==8 and heading<0):assert heading==predicted,rows[-1]
  if f>=350:break
 else:raise RuntimeError('probe did not finish')
 assert any(r['render'] and r['predicted']!=r['heading'] for r in rows)
 assert any(r['render'] and r['raw']==0 for r in rows)
 assert any(r['render'] and r['raw']==4 for r in rows)
 (s.out/'probe.json').write_text(json.dumps(dict(rows=rows,actions=actions,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('validated',len(rows),'player pose calls',actions,flush=True)
finally:s.quit()
