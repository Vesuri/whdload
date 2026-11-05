import sys,json,struct,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 sites={hex(a):read_bytes(s,a,10).hex() for a in (0x8b93a,0x8b97a,0x8b9a0,0x8b02e,0x89f48,0x89e70,0xa876c,0x8660e,0x8747e,0x86fa0,0x89d32,0x87736,0x870dc,0x8915a,0x8a8e2,0x875c8,0x8773c,0x8b486,0x8c5a8,0x8c8ae,0x8bbe6,0x8baec,0x8c130,0x8c48e,0x8cef0)}
 selected=os.environ.get('RR_RUNTIME_SELECTED')=='1'
 originals={0x8b93a:'20290026e088',0x8b97a:'c1c1e080082900050068',0x8b9a0:'33400022d1690000',0x8b02e:'33fcffff000a59e4',0x89f48:'2029000490b9000a5d1e',0x89e70:'94b9000a5d1e',0xa876c:'4ff900077cbe',0x8660e:'33fc0001000a6f00',0x8747e:'0c790020000a59da',0x86fa0:'33c1000a6f00',0x89d32:'5239000a5990',0x87736:'4eb9000aecba',0x870dc:'4a79000a7204',0x8915a:'2039000a7c02',0x8a8e2:'3229000cb3fc000a5d60',0x875c8:'4eb90008970e',0x8773c:'4eb9000b2b2c'}
 originals.update({570502: '08f90006000a', 574888: '41f9000909d0', 575662: '42790008b480', 572390: '48e7fffe3369', 572140: '3341003cd269', 573744: '42790008b484', 574606: '48e7ffff2079', 577264: '3029000449f9'})
 if selected:
  assert sites['0x8747e'].startswith('4ef9') and sites['0x8660e'].startswith('4eb9')
  target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCSTEP1');assert off>=0
  state=struct.unpack_from('>4I',data,off+8);assert state[0]>0 and state[1]>0 and state[3]==1,state
 else:
  for addr,prefix in originals.items():assert sites[hex(addr)].startswith(prefix),(hex(addr),sites)
  state=None
 (s.out/'dispatch.json').write_text(json.dumps(dict(selected=selected,state=state,sites=sites,provenance=provenance(os.environ['SLAVE'],s)),indent=2));print('selected',selected,'state',state,flush=True)
finally:s.quit()
