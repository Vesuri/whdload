from unicorn_b import *
import itertools,json
results=[]
for name in ('Gunship','GunshipNTSC'):
 c=CPU();f=build/'release'/f'{name}.Slave';c.put(base,bytes(BinFmt().load_image(str(f)).get_segments()[0].get_data()))
 syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',f.with_suffix('.lst').read_text(encoding='latin1'),re.M)}
 A=0x500000;H=0x510000;COP=0x520000
 def put(addr,n,v):c.put(addr,v.to_bytes(n,'big'))
 put(base+syms['timing_runtime_arena'],4,A);put(A+syms['RT_HUNKS']+24,4,H)
 put(base+syms['timing_display_pending'],2,0)
 cases=0
 for active,owner,boundary,timer,order,index,normal in itertools.product((0,1),(0,1),(0,1),(0,1,30),(0,31),(0,1),(0,0x123)):
  put(base+syms['timing_display_async'],2,active);put(A+syms['RT_CAPTURE_OWNER'],2,owner);put(A+syms['RT_BOUNDARY_PHASE'],2,boundary)
  put(H+0x4296,1,timer);put(H+0x40,4,COP+2);put(H+0x44,4,order);put(H+0x49ac,4,index)
  put(H+0x484c+index*64,2,normal)
  copper=b''.join(struct.pack('>HH',0x180+2*(i^order),0xf80) for i in range(32));c.put(COP,copper)
  c.rw(8,0x8f000);c.call(base+syms['timing_display_vbl'])
  expected=bytearray(copper)
  if active and owner and not boundary and not timer:struct.pack_into('>H',expected,order*4+2,normal)
  assert c.get(COP,128)==expected,(name,active,owner,boundary,timer,order,index,normal)
  assert c.get(H+0x4296,1)==bytes([timer]);cases+=1
 results.append(dict(release=name,cases=cases));c.close()
print(json.dumps(results,indent=2))
