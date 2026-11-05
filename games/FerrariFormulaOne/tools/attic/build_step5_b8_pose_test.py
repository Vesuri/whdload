from pathlib import Path
import struct,subprocess,json,random,math
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b8-pose-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0].replace('move.w sr','move.w ccr')
trig=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()[0x2180c:0x2180c+2560];table=struct.unpack('>1280h',trig)
def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
def angle(a,b,t):return (a+trunc(((b-a+512)%1024-512)*t,100))%1024
def expected(p,q,t,count):
 t=min(t,100);step=q[0]-p[0]
 if q[5] or p[5]!=q[5] or step not in (0,1,-1,count-1,1-count):return q,1
 theta=(q[3]-q[4]-p[3]+p[4])%1024 if step else 0
 x,z=p[1:3]
 if step:
  forward=step in (1,1-count)
  z-=512 if forward else 0
  sn,cs=table[theta],table[theta+256]
  x,z=(x*cs>>15)-(z*sn>>15),(x*sn>>15)+(z*cs>>15)+(0 if forward else 512)
 return [q[0],x+trunc((q[1]-x)*t,100),z+trunc((q[2]-z)*t,100),angle(p[3],q[3],t),angle(p[4]-theta,q[4],t),q[5]],0
cases=[];rng=random.Random(0xB8)
for step in (0,1,-1,239,-239,2,-2):
 for theta in (0,1,31,993,256,512):
  for t in (0,1,20,40,60,80,99,100,101):
   seg=0 if step>=0 else -step
   yaw=rng.randrange(1024);p=[seg,rng.randrange(-400,401),rng.randrange(512),yaw,yaw,0];newyaw=rng.randrange(1024)
   q=[seg+step,rng.randrange(-400,401),rng.randrange(512),newyaw,(newyaw-theta)%1024,0]
   e,ret=expected(p,q,t,240);cases.append(dict(p=p,q=q,t=t,count=240,expected=e,ret=ret))
for ps,qs in ((0,1),(-1,0),(0,-25),(-25,-25)):
 p=[3,-12,300,1020,12,ps];q=[3,35,350,4,20,qs];e,ret=expected(p,q,50,240);cases.append(dict(p=p,q=q,t=50,count=240,expected=e,ret=ret))
for x,z in ((-32768,32767),(32767,-32768),(-1,1),(0,0)):
 for yaw,newyaw in ((1023,0),(0,1023),(0,512),(512,0)):
  for t in (0,1,50,99,100):
   p=[3,x,z,yaw,yaw,0];q=[3,z,x,newyaw,newyaw,0];e,ret=expected(p,q,t,240);cases.append(dict(p=p,q=q,t=t,count=240,expected=e,ret=ret))
(o/'inputs.bin').write_bytes(b''.join(struct.pack('>14h',*c['p'],*c['q'],c['t'],c['count']) for c in cases));(o/'trig.bin').write_bytes(trig);(o/'expected.json').write_text(json.dumps(cases,indent=2)+'\n')
s=prefix+f''' lea inputs(pc),a4
 lea results(pc),a5
 move.w #{len(cases)-1},d6
.loop:
 move.l a4,a0
 lea 12(a4),a1
 move.l a5,a2
 lea trig(pc),a3
 move.w 24(a4),d0
 move.w 26(a4),d1
 bsr.w FF1BlendRenderPose
 move.l d0,12(a5)
 lea 28(a4),a4
 lea 16(a5),a5
 dbra d6,.loop
 rts
 include "FerrariFormulaOne_RenderPose.s"
installed: dc.l 0
trig: incbin "trig.bin"
inputs: incbin "inputs.bin"
results: ds.b {len(cases)*16}
'''
(o/'pose.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_RENDER_POSES=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','pose.list','-o','pose.bin','pose.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'pose.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'pose.slave').write_bytes(h+code+bytes.fromhex('000003f2'));print(len(cases),'pose cases')
