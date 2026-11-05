from pathlib import Path
import re,struct,subprocess,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b4-scalar-hooks-v4';o.mkdir(parents=True,exist_ok=True);base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
addresses=[int(a,16) for a in ('672f0','673fc','67426','67438','6744a','67476','675c0','6766c','6768e','676e0')]
cases=[]
extra='scalar_fixture:\n'
for a in addresses:extra+=f' move.w #$4e75,${a+6:x}\n'
extra+=' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n clr.w $32fbc\n'
for a in addresses:
 for q,rem,proposal in [(0,0,-1),(0x11234,4,5),(500<<16,0,1000),((450<<16)+65535,-4,-100),((200<<16)+0x8765,-2,200),(0x11111,3,0)]:
  i=len(cases);total=((proposal-(q>>16))<<16)+rem;delta=(abs(total)//5)*(1 if total>=0 else -1);new=q+delta;nr=total-delta*5
  if new<0 or (new==0 and nr<0):new=nr=0
  if new>500<<16 or (new==500<<16 and nr>=0):new=500<<16;nr=0
  cases.append(dict(site=hex(a),before=q,rem=rem,proposal=proposal,expected_speed=new>>16,expected_q16=new,expected_rem=nr))
  extra+=f' lea speed_work(pc),a0\n move.l #${q:08x},(a0)\n move.w #{rem},4(a0)\n'
  for k in range(1,8):extra+=f' move.l #${0x10101010+k:08x},d{k}\n'
  for k in range(7):extra+=f' movea.l #${0x20202020+k:08x},a{k}\n'
  extra+=f' move.l #{proposal},d0\n move.w #31,ccr\n bsr.w velocity_{a:x}\n movem.l d0-d7/a0-a6,-(sp)\n move.w ccr,-(sp)\n move.l sp,a0\n lea (scalar_results+{i*72}.l,pc),a1\n moveq #30,d0\n.copy{i}:\n move.w (a0)+,(a1)+\n dbra d0,.copy{i}\n move.l speed_work(pc),(a1)+\n move.w speed_work+4(pc),(a1)+\n move.w $32fbe,(a1)+\n clr.w (a1)+\n adda.w #62,sp\n'

for address,axis in [(0x678de,0),(0x67900,1),(0x67948,0),(0x67976,1)]:
 extra+=f' move.w #$4e75,${address+6:x}\n'
extra+=' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n'
for address,axis in [(0x678de,0),(0x67900,1),(0x67948,0),(0x67976,1)]:
 native=0x32fb4+axis*4
 for before,rem,inc in [(0,4,1),(0,-4,-1),(0x7fffffff,2,1000),(0x80000000,-2,-1000),(0xffffffff,-4,2147483643)]:
  total=inc+rem;delta=(abs(total)//5)*(1 if total>=0 else -1);after=(before+delta)&0xffffffff;nr=total-delta*5;i=len(cases)
  cases.append(dict(kind='heading',site=hex(address),before=before,rem=rem,proposal=inc,expected_q16=after,expected_rem=nr))
  extra+=f' lea heading_shadow+{axis*6}(pc),a0\n move.l #${before:08x},(a0)\n move.w #{rem},4(a0)\n move.l #${before:08x},${native:x}\n'
  for k in range(1,8):extra+=f' move.l #${0x10101010+k:08x},d{k}\n'
  for k in range(7):extra+=f' movea.l #${0x20202020+k:08x},a{k}\n'
  extra+=f' move.l #{inc},d0\n move.w #31,ccr\n bsr.w heading_{address:x}\n movem.l d0-d7/a0-a6,-(sp)\n move.w ccr,-(sp)\n move.l sp,a0\n lea (scalar_results+{i*72}.l,pc),a1\n moveq #30,d0\n.copy{i}:\n move.w (a0)+,(a1)+\n dbra d0,.copy{i}\n move.l heading_shadow+{axis*6}(pc),(a1)+\n move.w heading_shadow+{axis*6+4}(pc),(a1)+\n move.l ${native:x},(a1)+\n adda.w #62,sp\n'

extra+=' lea scalar_complete(pc),a0\n move.l #1,(a0)\n rts\nscalar_stop:\n bra.b scalar_stop\nscalar_complete: dc.l 0\n'
for variant in ('verify','lean'):
 s=(r/f'tmp/build/step5-b4-v4/{variant}/fine.s').read_text().replace(' bsr.w FF1InstallOpponents',' bsr.w FF1InstallOpponents\n bsr.w scalar_fixture\n bra.l scalar_stop')
 s=s.replace(' include "FerrariFormulaOne_UpdateHooks.s"',(r.parents[1]/'Games/FerrariFormulaOne_UpdateHooks.s').read_text())
 s=s.replace('\n FF1UpdateWorkspace','\n'+extra+'\n FF1UpdateWorkspace')+f'\nscalar_results: ds.b {len(cases)*72}\n'
 for label in ('velocity_records','velocity_target_speeds','speed_feedback_records','fine_records','heading_records','position_velocity_inputs','steering_records','wear_records','events_records','clocks_records','counters_records','fuel_records','boost_records','recovery_records','recovery_contact_records','schedule_records'):
  s=re.sub(r'^'+label+r': ds\.[bl] \d+$',label+': ds.b 80',s,flags=re.M)
 s=re.sub(r'^heading_records: ds.b \d+$','heading_records: ds.b 512',s,flags=re.M)
 s=re.sub(r'^speed_records: ds.b \d+$','speed_records: ds.b 2048',s,flags=re.M)
 (o/(variant+'.s')).write_text(s);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-b4-v4/lean/original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-I'+str(r.parents[1]/'Games'),'-L',variant+'.list','-o',variant+'.bin']
 if variant=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+[variant+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',(o/(variant+'.list')).read_text(),re.M)[1],16);assert len(code)+entry<32768;struct.pack_into('>H',code,24,len(code)+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(variant+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/(variant+'.slave')).write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');print(len(cases),'scalar wrapper cases per arm')
