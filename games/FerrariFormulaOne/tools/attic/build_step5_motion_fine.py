from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-motion-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
v=(r/'tmp/build/step5-velocity-fine/fine.s').read_text().split('velocity_records: ds.b 64000')[0]
v=v.replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_velocity\n',' bsr.w install_velocity\n bsr.w install_position_bridge\n bsr.w install_fine_position\n bsr.w install_heading\n',1)
h=(r/'tmp/build/step5-heading-fine/heading.s').read_text();h=h[h.index('install_position_bridge:'):]
h=h.replace('fine_records: ds.b 25600\n','').replace('heading_records: ds.b 38400\n','')
h='\n'.join(line for line in h.splitlines() if 'include ' not in line or 'FerrariFormulaOne_Step.s' not in line)+'\n'
h=h.replace('cmpi.w #9,d0','cmpi.w #8,d0').replace('FF1PositionRotate20','FF1PositionRotate25').replace('FF1PositionCrossed020','FF1PositionCrossed25')
h=h.replace('fine_stop:\n bra.b fine_stop','fine_stop:\n bra.w velocity_stop')
old=''' move.w $32f94,d0
 bsr.w FF1Position20
 tst.l d1
 bne.w fine_fault
 addq.l #6,a0
 move.w $32f96,d0
 bsr.w FF1Position20'''
new=''' move.l a0,a5
 bsr.w velocity_context
 move.l a0,a2
 move.l a5,a0
 move.l fine_steps(pc),d0
 mulu.w #12,d0
 lea (position_velocity_inputs.l,pc),a1
 adda.l d0,a1
 move.l (a2),(a1)
 move.l 4(a2),4(a1)
 move.l 8(a2),8(a1)
 move.l (a2),d0
 move.w 8(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 bne.w fine_fault
 addq.l #6,a0
 move.l 4(a2),d0
 move.w 10(a2),d1
 bsr.w FF1Position20Velocity'''
assert old in h;h=h.replace(old,new,1)
asm=v+h+'''velocity_records: ds.b 64000
velocity_target_speeds: ds.l 800
speed_records: ds.b 131072
speed_feedback_records: ds.b 6400
fine_records: ds.b 25600
heading_records: ds.b 38400
position_velocity_inputs: ds.b 9600
'''
# Record buffers deliberately follow all code; use full 020 PC displacements.
asm=re.sub(r'lea ([A-Za-z_][A-Za-z_0-9+]*)(\(pc\)),',r'lea (\1.l,pc),',asm)
# Reject overlaps among independent installers before producing a fixture.
hooks=[]
for folder in ('step5-velocity-fine','step5-position-fine','step5-heading-fine'):
 hooks.extend(json.loads((r/'tmp/build'/folder/'hooks.json').read_text()))
hooks.extend([(0x67a04,6,'fine_advance'),(0x67a36,6,'fine_boundary'),(0x68292,6,'fine_bounds')])
for i,(a,n,*_) in enumerate(hooks):
 for b,m,*_ in hooks[i+1:]:assert a+n<=b or b+m<=a,(hex(a),hex(b),'hook overlap')
(o/'hooks.json').write_text(json.dumps(hooks,indent=2)+'\n')
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v6/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built combined motion diagnostic:',len(hooks),'qualified hooks')
