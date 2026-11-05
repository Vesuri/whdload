from pathlib import Path
import ast,re,struct,subprocess,json
r=Path(__file__).resolve().parents[1];games=r.parents[1]/'Games';o=r/'tmp/build/step5-b4-contacts-v4';o.mkdir(parents=True,exist_ok=True)
tree=ast.parse((r/'tools/build_step5_native_contact.py').read_text());extra=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='extra' for t in n.targets))
extra=extra.replace('blo.b seed_loop','blo.w seed_loop')
extra=extra.replace('move.w #55,d7','move.w #111,d7').replace(' clr.w $1c21e',' move.w 6(a3),d0\n lea events_pulse(pc),a0\n move.w d0,(a0)\n clr.w $1c21e',1)
extra=extra.replace(' move.w (a3)+,d2',' move.w (a3)+,d2\n addq.l #2,a3',1)
extra=extra.replace(' clr.w (a1,d0.l)\n clr.w (a1,d1.l)',''' IFD B3_CONTACT_CONTROL
 tst.w events_pulse(pc)
 bne.b .active
 tst.w d0
 bne.b .inactive
.active:
 ENDC
 clr.w (a1,d0.l)
 clr.w (a1,d1.l)
.inactive:''',1)
extra=extra.replace(' lea $6f14c,a1\n move.w #100,(a1,d0.l)', ' lea $6f13c,a1\n clr.w (a1,d0.l)\n lea $6f14c,a1\n move.w #100,(a1,d0.l)',1)
a=extra.index(' movem.l d0-d7/a0-a6,-(sp)\n jsr $68d4e')
extra=extra[:a]+''' ; Seed all velocity and speed shadows with distinct, nonzero tails.
 lea velocity_shadow(pc),a0
 lea speed_shadow(pc),a1
 moveq #0,d6
.seed_other:
 clr.w (a0)
 move.w #$1234,2(a0)
 move.w #3,8(a0)
 move.w #4,10(a0)
 move.w #$5678,6(a0)
 move.l d6,d0
 add.w d0,d0
 move.w $6f14c(d0.l),4(a0)
 move.w $2275a(d0.l),(a1)
 move.w #$4321,2(a1)
 move.w #2,4(a1)
 adda.w #12,a0
 addq.l #6,a1
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .seed_other
'''+extra[a:]
a=extra.index(' lea position_shadow(pc),a0\n moveq #23,d6\nsave_shadow:');b=extra.index(' dbra d7,case_loop',a)
extra=extra[:a]+''' lea $6a62a,a0
 moveq #3,d6
.save_pos:
 move.l (a0)+,(a4)+
 dbra d6,.save_pos
 lea $2275a,a0
 moveq #3,d6
.save_speed:
 move.l (a0)+,(a4)+
 dbra d6,.save_speed
 lea $6f14c,a0
 moveq #3,d6
.save_vel:
 move.l (a0)+,(a4)+
 dbra d6,.save_vel
 lea $6f13c,a0
 moveq #3,d6
.save_x:
 move.l (a0)+,(a4)+
 dbra d6,.save_x
 lea position_shadow(pc),a0
 moveq #23,d6
.save_ps:
 move.l (a0)+,(a4)+
 dbra d6,.save_ps
 lea velocity_shadow(pc),a0
 moveq #23,d6
.save_vs:
 move.l (a0)+,(a4)+
 dbra d6,.save_vs
 lea speed_shadow(pc),a0
 moveq #11,d6
.save_ss:
 move.l (a0)+,(a4)+
 dbra d6,.save_ss
'''+extra[b:]
cases=[dict(first=a,second=b,front=f,pulse=p) for p in (0,1) for a in range(7) for b in range(a+1,8) for f in (0,1)]
extra+=''.join(f" dc.w {c['first']},{c['second']},{c['front']},{c['pulse']}\n" for c in cases)+f'contact_results: ds.b {len(cases)*304}\n'

for name in ('position_shadow','velocity_shadow','speed_shadow'):
 extra=extra.replace(name,'fixture_'+name)
before='';after=''
for name,size in [('position_shadow',12),('velocity_shadow',12),('speed_shadow',6)]:
 for off in range(0,size,2):
  before+=f' move.w fixture_{name}+{off}(pc),d0\n lea {name}+{off}(pc),a0\n move.w d0,(a0)\n'
  after+=f' move.w {name}+{off}(pc),d0\n lea fixture_{name}+{off}(pc),a0\n move.w d0,(a0)\n'
extra=extra.replace(' jsr $68d4e',before+' jsr $68d4e'+ '\n'+after)
extra+='fixture_position_shadow: ds.b 96\nfixture_velocity_shadow: ds.b 96\nfixture_speed_shadow: ds.b 48\n'

(o/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
for variant in ('control','candidate'):
 s=(r/'tmp/build/step5-b4-v4/lean/fine.s').read_text()
 if variant=='control':s=re.sub(r'^ bsr.w (install_\w+|FF1Install\w+|schedule_install)\n','',s,flags=re.M)
 s=s.replace(' bsr.w schedule_begin',' cmpi.l #126,ticks(pc)\n bne.b .no_fixture\n bsr.w contact_fixture\n.no_fixture:',1)
 # Both fixture arms execute only the native contact routine, never a tick.
 # Explicit cache flush precedes entry since the control omits scheduler setup.
 s=s.replace(' bsr.w contact_fixture',' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n bsr.w contact_fixture',1)
 s=s.replace('\n FF1UpdateWorkspace',extra+'\n FF1UpdateWorkspace')
 (o/f'{variant}.s').write_text(s);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-b4-v4/lean/original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(games),'-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-L',variant+'.list','-o',variant+'.bin']
 if variant=='control':args+=['-DB3_CONTACT_CONTROL=1']
 subprocess.run(args+[variant+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);size=len(code);entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',(o/(variant+'.list')).read_text(),re.M)[1],16);assert size+entry<32768
 struct.pack_into('>H',code,24,size+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/(variant+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/(variant+'.slave')).write_bytes(h+code+bytes.fromhex('000003f2'))
print('Built',len(cases),'cases per arm')
