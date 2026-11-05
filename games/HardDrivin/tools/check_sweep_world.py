"""Run native collision with world objects omitted from its scene list."""
from pathlib import Path
from fractions import Fraction
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
scenarios=[[(0,0,5000,1,8,1)],[(0,0,6000,1,8,1),(0,0,5000,1,8,1)],[(0,0,5000,1,8,1),(0,0,6000,1,8,1)],[(0,0,5000,0,8,1)],[(0,0,5000,1,7,1)],[(0,0,5000,1,8,95)],[(5000,0,5000,1,8,1)],[(0,5000,5000,1,8,1)],[(0,0,-1000,1,8,1)],[(0,0,32760,1,8,1)],[(0,0,-32760,1,8,1)],[(0,0,5000,1,8,1),(0,0,5000,1,8,1)]]
results=[]
try:
 for enabled in [False,True]:
  for fields in [8,640]:
   for scene_contact in [False,True]:
    for objects in scenarios:
     depths=objects
     ok(u.uc_close(h));h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x100000,0x400000,7))
     for index,hu in enumerate(hunks()):
      b=bytearray(hu['data'])
      for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
      write(bases[index],bytes(b))
     write(0x400100,module)
     write(a4-0x7fce,bytes.fromhex('4e75'));write(a4-0x7fe0,bytes.fromhex('4e75'))
     if enabled:
      write(codebase+0xbd0e,bytes.fromhex('4ef9')+struct.pack('>I',0x400106));write(codebase+0xbd14,bytes.fromhex('4eb9')+struct.pack('>I',0x40010c))
     pack(g(0xb190),'h',int(scene_contact));write(g(0xe931),b'\x00');write(g(0xe960),b'\x00');pack(g(0xe93a),'4h',0,16384,0,16384)
     if scene_contact:
      pack(g(0xaf38),'HI',0,0x360000);pack(0x360000,'3h',0,0,25);write(0x360019,b'\x01');write(0x36001c,b'\x08');write(0x360022,b'\xff')
     # Offset camera proves use of world coordinates rather than stale raw XYZ.
     camera=(123,45,67);pack(g(0x98ea),'3h',*camera)
     pack(g(0x9962),'Ih',0x350000,len(objects))
     for i,(x,y,z,active,cls,typ) in enumerate(objects):
      obj=0x350000+56*i;write(obj,bytes(56));pack(obj,'3h',-9999,11111,-12345)
      coords=[(v+c+32768)%65536-32768 for v,c in zip((x,y,z),camera)]
      pack(obj+8,'3h',*coords);write(obj+25,bytes([typ]));write(obj+28,bytes([cls]));write(obj+30,bytes([active]))
     untouched=read(0x350000,len(objects)*56)
     pack(g(0xaf04),'h',0);write(g(0x9606),b'\x00');pack(g(0x9928),'h',400);pack(g(0x992c),'h',112);pack(g(0x991e),'3h',0,0,600)
     start=[c*8 for c in camera];pack(g(0x98fc),'3i',*start);write(0x407018,b'\xff');pack(0x407100,'H',fields);call(0x400100)
     pack(g(0x9904),'i',start[2]+48000);call(codebase+0xbaee)
     eligible=[(Fraction(max(0,z-77),6000),i) for i,(x,y,z,active,cls,typ) in enumerate(objects) if active and cls==8 and typ!=95 and -44<=x<=44 and -44<=y<=44 and 3<=z<=6077]
     hit=enabled and fields>8 and bool(eligible) and not scene_contact
     actual_z=struct.unpack('>i',read(g(0x9904),4))[0]
     crash=read(g(0x9606),1)[0];hits,overflow,_,_,_= (0,0,0,0,0)
     hits=struct.unpack('>I',read(state+58,4))[0];overflow=struct.unpack('>I',read(state+62,4))[0]
     assert crash==(25 if hit or scene_contact else 0),(enabled,fields,objects,crash)
     if hit:
      fraction,index=min(eligible);expected_z=start[2]+int(48000*fraction)-1200
      assert actual_z==expected_z,(actual_z,expected_z,objects)
      assert struct.unpack('>I',read(state+42,4))[0]==0x350000+56*index
     else:assert actual_z==start[2]+48000-(1200 if scene_contact else 0)
     assert hits==int(hit) and overflow==0,(objects,hits,overflow)
     assert read(0x350000,len(objects)*56)==untouched
     results.append(dict(enabled=enabled,fields=fields,scene_contact=scene_contact,objects=objects,added_hit=hit))
 report=dict(passed=True,cases=len(results),added_contacts=sum(x['added_hit'] for x in results),scope='Actual pristine collision loop with tracked sweep and private main-world pool. Scene list omits world objects, stale raw coordinates, translated camera, culling-distance crossings, irrelevant/inactive objects, ordering/ties, native priority, word-edge distant rejection, and no object-record mutation. No natural-route or FPS acceptance.',results=results)
 Path('tmp/sweep-world-check.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='results'})
finally:ok(u.uc_close(h))
