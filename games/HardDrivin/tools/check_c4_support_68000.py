from pathlib import Path
import ctypes as C,json,os,random,struct,subprocess
exec(Path('tools/check_c4_support_faces.py').read_text().split("faces=raw[")[0])
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
stem=Path('tmp/c4-support-face');stem.with_suffix('.s').write_text(' org $10000\n'+Path('tools/c4_support_face.s').read_text());subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x10000,stem.with_suffix('.bin').read_bytes())
rng=random.Random(713);cases=0
try:
 tests=[]
 for face in raw['unclipped_object_faces']:
  for x in [-30,0,30]:
   for z in [-45,0,45]:tests.append((face['vertices'],x,z))
 for i in range(10000):
  w=rng.randint(1,500);l=rng.randint(1,500);sx=rng.randint(-500,500);sz=rng.randint(-500,500);cx=rng.randint(-1000,1000);cz=rng.randint(-1000,1000)
  vertices=[[cx+w*s+sx*t,0,cz+sz*s+l*t] for s,t in [(-1,-1),(-1,1),(1,1),(1,-1)]]
  if i%2:vertices.reverse()
  x,z=(vertices[0][0],vertices[0][2]) if i%10==0 else (rng.randint(-1000,1000),rng.randint(-1000,1000))
  tests.append((vertices,x,z))
 for vertices,x,z in tests:
  expected=support(vertices,x,z) is not None
  write(0x20000,struct.pack('>'+str(3*len(vertices))+'h',*(v for p in vertices for v in p)))
  reg(17,0x2000);reg(2,0x20000);reg(9,len(vertices));reg(10,x&65535);reg(11,z&65535);reg(8,0x4f000);pack(0x4f000,'I',0x19000)
  ok(u.uc_emu_start(h,0x10000,0x19000,1000000,1000));assert reg(18)==0x19000 and reg(8)==0x4f004
  assert reg(9)==int(expected),(cases,vertices,x,z,expected,reg(9));cases+=1
 report=dict(passed=True,cases=cases,scope='Assembled finite convex upward car-space face coverage versus rational oracle: saved jump faces and random affine quads, reverse winding, edges. Not runtime integration or world-up policy.')
 Path('tmp/c4-support-68000-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
