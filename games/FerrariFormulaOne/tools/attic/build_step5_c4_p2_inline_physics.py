from pathlib import Path
import struct,subprocess,json,random,math
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-p2-inline-physics';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
rng=random.Random(0xc4200);mask=2**32-1;lo=-2**31;hi=2**31-1
cases=[]
def add(op,x,z,vx=0,vz=0,c=0,s=0):
 out=[0x12345678,0x76543210];status=0
 if op==0:out=[(vx-x)//2,(vz-z)//2]
 if op==1:
  out=[x+2*vx,z+2*vz]
  if not all(lo<=q<=hi for q in [2*vx,2*vz,*out]):out=[x,z];status=-1
 if op==2:
  out=[(x*c-z*s)//32768,(x*s+z*c)//32768]
  if not all(lo<=q<=hi for q in out):out=[x,z];status=-1
 if op==3:
  out=[c*s//32768,c*vx//32768]
  if not all(lo<=q<=hi for q in out):out=[0x12345678,0x76543210];status=-1
 if op==4:
  mag=math.isqrt(x*x+z*z);out[0]=0 if mag<4*65536 else min(mag,500*65536)
 if op==5:
  out=[x,z]
  if not 0<=x<=500*65536 or not -32768<=c<=32767:status=-1
  else:out[0]=min(max(x+2*(c-(x//65536))*65536,0),500*65536)
 if op==6:
  out=[c,z]
  if x<0 or c<0:status=-1
  else:out[0]=min(2*c,x)
 if op==7:
  a,b=x&65535,z&65535
  out=[vx*65536+(a*c-b*s)//32768,vz*65536+(a*s+b*c)//32768]
  if not all(lo<=q<=hi for q in out):out=[x,z];status=-1
 if op==8:
  v=x*c+(z-512*65536)*s
  out=[int(v>=0 if s>0 else v<=0),0x76543210] if s else [0,0x76543210]
  if not s:status=-1
 if op==9:out=[(x+2*c)&mask,z]
 if op==10:
  out=[x,z]
  if not 0<=x<=500*65536 or not -32768<=c<=32767 or not 0<=s<=2:status=-1
  else:out[0]=min(max(x+s*(c-(x//65536))*65536,0),500*65536)
 if op==11:
  phases=[(c-1)%4,c]
  allowed=lambda p:not ((s==4 and p==0) or (s==5 and p<2))
  out=[sum(allowed(p) for p in phases) if 0<=c<=3 else -1,0x76543210];status=s
 cases.append([op,x,z,vx,vz,c,s,*out,status])
edges=[lo,lo+1,-500*65536,-65537,-1,0,1,65535,500*65536,hi-1,hi]
for x in edges:
 for z in edges:
  add(0,x,z,z,x);add(1,x,z,z,x)
  add(4,x,z)
  for c,s in [(32767,0),(0,32767),(-32768,0),(0,-32768),(23170,-23170),(-32768,-32768)]:add(2,x,z,c=c,s=s)
for _ in range(350):
 x,z,vx,vz=[rng.randint(lo,hi) for _ in range(4)]
 add(0,x,z,vx,vz);add(1,x,z,vx,vz);add(2,x,z,c=rng.randint(-32768,32767),s=rng.randint(-32768,32767));add(4,x,z)
for x in edges:
 for c in [-32768,-1,0,1,32767]:
  for s in [-32768,-1,0,1,32767]:add(3,0,0,vx=c,c=x,s=s)
for x in [-1,0,1,65535,65536,65537,499*65536+65535,500*65536,500*65536+1]:
 for proposal in [-32769,-32768,-1,0,1,4,499,500,501,32767,32768]:add(5,x,123,c=proposal)
for x in [-1,0,1,9,65535,hi]:
 for loss in [-1,0,1,5,32768,hi]:add(6,x,123,c=loss)
for x in edges:
 for z in edges:
  for c,s in [(0,1000),(29,999),(-29,999),(32767,-32768),(0,0)]:add(8,x,z,c=c,s=s)
  for c,s in [(32767,0),(-32768,-32768),(23170,23170)]:
   for vx,vz in [(0,0),(32767,-32768),(-32768,32767)]:add(7,x,z,vx,vz,c,s)
  for delta in [lo,-1,0,1,hi]:add(9,x,z,c=delta)
for x in [-1,0,1,65535,65536,65537,499*65536+65535,500*65536,500*65536+1]:
 for proposal in [-32769,-32768,-1,0,1,4,499,500,501,32767,32768]:
  for pulses in [-1,0,1,2,3]:add(10,x,123,c=proposal,s=pulses)
for phase in [-1,0,1,2,3,4,32767]:
 for setting in [-1,0,1,2,3,4,5,6,32767]:add(11,0,0,c=phase,s=setting)
# Straight-segment boundaries, both signs of cosine, undefined zero cosine.
for x in edges:
 for z in [lo,lo+1,-1,0,512*65536-1,512*65536,512*65536+1,hi-1,hi]:
  for cosine in [-32768,-1000,-1,0,1,999,32767]:add(8,x,z,c=0,s=cosine)
(o/'cases.bin').write_bytes(b''.join(struct.pack('>10I',*(v&mask for v in c)) for c in cases))
start=(r/'tmp/build/step5-c3-track-test/track.s').read_text().split('tests:')[0]
s=start+'''tests:
 lea cases(pc),a4
 move.w #COUNT-1,d7
.loop:
 lea vector(pc),a0
 move.l 4(a4),(a0)
 move.l 8(a4),4(a0)
 lea rhs(pc),a1
 move.l 12(a4),(a1)
 move.l 16(a4),4(a1)
 lea output(pc),a2
 move.l #$12345678,(a2)
 move.l #$76543210,4(a2)
 move.l 20(a4),d0
 move.l 24(a4),d1
 move.l 12(a4),d2
 move.l #$abcdef01,d3
 move.l #$76543210,d4
 move.l #$fedcba98,d5
 move.l #$43218765,d6
 move.l sp,a3
 tst.l (a4)
 beq.w .derivative
 cmpi.l #1,(a4)
 beq.w .apply
 cmpi.l #2,(a4)
 beq.w .rotate
 cmpi.l #3,(a4)
 beq.w .project
 cmpi.l #4,(a4)
 beq.w .speed
 cmpi.l #5,(a4)
 beq.w .rate
 cmpi.l #7,(a4)
 beq.w .position_rotate
 cmpi.l #8,(a4)
 beq.w .crossed
 cmpi.l #9,(a4)
 beq.w .heading
 cmpi.l #10,(a4)
 beq.w .weighted
 cmpi.l #11,(a4)
 beq.w .phase
 bsr.w FF1Wear200Delta
 move.l d0,(a2)
 move.l 4(a0),4(a2)
 bra.w .check
.apply:
 bsr.w FF1VelocityApply200
 bra.b .copy
.rotate:
 bsr.w FF1VelocityRotate000
 bra.b .copy
.project:
 move.l a2,a0
 bsr.w FF1VelocityProject000
 bra.w .check
.speed:
 move.l a2,a1
 bsr.w FF1SpeedFromVelocity000
 bra.w .check
.rate:
 bsr.w FF1SpeedRate200
.copy:
 move.l (a0),(a2)
 move.l 4(a0),4(a2)
 bra.w .check
.derivative:
 bsr.w FF1VelocityDerivative200
 bra.w .check
.weighted:
 bsr.w FF1SpeedRatePulses200
 bra.w .copy
.phase:
 bsr.w FF1PhasePulses200
 move.l d0,(a2)
 bra.w .check
.position_rotate:
 move.l d3,-(sp)
 move.l 16(a4),d3
 bsr.w FF1PositionRotate200
 move.l (sp)+,d3
 bra.w .copy
.crossed:
 bsr.w FF1PositionCrossed000
 move.l d0,(a2)
 bra.w .check
.heading:
 bsr.w FF1Heading200
 moveq #0,d1
 bra.w .copy
.check:
 cmp.l 36(a4),d1
 bne.w .bad
 move.l (a2),d0
 cmp.l 28(a4),d0
 bne.w .bad
 move.l 4(a2),d0
 cmp.l 32(a4),d0
 bne.w .bad
 cmp.l 12(a4),d2
 bne.b .bad
 cmpi.l #$abcdef01,d3
 bne.b .bad
 cmpi.l #$76543210,d4
 bne.b .bad
 cmpi.l #$fedcba98,d5
 bne.b .bad
 cmpi.l #$43218765,d6
 bne.b .bad
 cmpa.l sp,a3
 bne.b .bad
 lea checked(pc),a1
 addq.l #1,(a1)
 adda.w #40,a4
 dbra d7,.loop
 rts
.bad:
 lea error(pc),a1
 move.l #1,(a1)
 lea failed_case(pc),a1
 move.l a4,(a1)+
 move.l (a2),(a1)+
 move.l 4(a2),(a1)+
 move.l d1,(a1)+
 move.l d7,(a1)+
 rts
 include "FerrariFormulaOne_Wide000.s"
 include "FerrariFormulaOne_Physics200.s"
 include "FerrariFormulaOne_Position200.s"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 12
vector: ds.l 2
rhs: ds.l 2
output: ds.l 2
cases: incbin "cases.bin"
'''.replace('COUNT',str(len(cases)))
(o/'physics.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_C4_MUL_INLINE=1','-DFF1_C4_MUL_INLINE_TEST=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','physics.list','-o','physics.bin','physics.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'physics.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'physics.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases),scope='Python integer arithmetic model, atomic error rollback, register/stack checks for twelve 200 ms conversion primitives'))+'\n')
s=(r/'tools/test_step5_c4_wide.py').read_text().replace('step5-c4-wide','step5-c4-p2-inline-physics').replace('c4-wide-oracle','c4-p2-inline-physics-oracle').replace('wide.list','physics.list').replace('wide.slave','physics.slave').replace('FerrariFormulaOne_Wide000.s','FerrariFormulaOne_Physics200.s')
(r/'tools/test_step5_c4_p2_inline_physics.py').write_text(s)
print('Built',len(cases),'physics conversion cases')
