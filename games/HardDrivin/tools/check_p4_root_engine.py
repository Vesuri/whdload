"""Two independent 68000 engines compare the complete native engine around the phase hook."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0xfb0000,7));handles=[h]
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0,0x1000000,7));handles.append(h)
root=Path('tmp/prof/p4-check-motion');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4']
listing=Path('tmp/build/p4-check-motion.lst').read_text(encoding='latin1')
sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)}
base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()};ph=sy['_phase_state'];ss=sy['_time_scalar_state'];dt=sy['_drivetrain_state'];stop=0x41000;sp=0x4f000
phase=Path('src/HardDrivinPhase.s').read_text();block=phase[phase.index('_phase_gear:'):phase.index(' ; Skids retain')]
private=base+0x9500
source=f" org ${private:x}\n"+phase[phase.index('PH_VALID equ'):phase.index(" dc.b 'HDPHASE1'")]
for name in ['_phase_state','_phase_scalar_step','_phase_tail_ptr','_phase_manual_ptr']:source+=f'{name} equ ${sy[name]:x}\n'
source+=block+'\n';stem=Path('tmp/p4-engine-entry');stem.with_suffix('.s').write_text(source)
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
newcode=stem.with_suffix('.bin').read_bytes()
patches=[(private,newcode),(sy['_phase_gear'],bytes.fromhex('4ef9')+struct.pack('>I',private))];private+=len(newcode)+16
scalar=Path('src/HardDrivinScalar.s').read_text()
ss_equ=scalar[scalar.index('SS_VELOCITY_CARRY equ'):scalar.index('_time_scalar_fields:')]
ph_equ=phase[phase.index('PH_VALID equ'):phase.index(" dc.b 'HDPHASE1'")]
for name,end in [('_time_rpm_engaged','_time_rpm_delta:'),('_time_velocity_add','_time_throttle_up:'),('_time_rpm_delta','_time_reset_scalars:'),('_time_throttle_retention','_time_initial_scalars:')]:
 block=scalar[scalar.index(name+':'):scalar.index(end,scalar.index(name+':'))]
 src=f' org ${private:x}\nVERIFY_DRIVETRAIN_PHASE equ 1\nVERIFY_TIME_DISSIPATION equ 1\n'+ss_equ+ph_equ
 for symbol in ['_phase_state','_time_scalar_state','_time_scalar_fields','_time_scale_word','_time_limit_dissipation','_decay_throttle']:src+=f'{symbol} equ ${sy[symbol]:x}\n'
 if name=='_time_rpm_engaged':src+=f"_time_rpm_delta equ ${sy['_time_rpm_delta']:x}\n"
 src+=block+'\n';target=Path('tmp/p4-entry'+name);target.with_suffix('.s').write_text(src)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(target.with_suffix('.bin')),str(target.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 body=target.with_suffix('.bin').read_bytes();patches.extend([(private,body),(sy[name],bytes.fromhex('4ef9')+struct.pack('>I',private))]);private+=len(body)+16
drive=Path('src/HardDrivinDrivetrain.s').read_text()
for name in ['_drivetrain_power','_drivetrain_sqrt']:
 block=drive[drive.index(name+':'):drive.index('\n\tENDC',drive.index(name+':'))]
 src=f' org ${private:x}\n'
 for symbol in ['_drivetrain_state',name+'_state']:src+=f'{symbol} equ ${sy[symbol]:x}\n'
 target=Path('tmp/p4-entry'+name);target.with_suffix('.s').write_text(src+block+'\n')
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(target.with_suffix('.bin')),str(target.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 body=target.with_suffix('.bin').read_bytes();patches.extend([(private,body),(sy[name],bytes.fromhex('4ef9')+struct.pack('>I',private))]);private+=len(body)+16
lookup=phase[phase.index('_phase_power:'):]
target=Path('tmp/p4-power-entry');src=f' org ${private:x}\n'+ph_equ
for symbol in ['_phase_state','_drivetrain_power']:src+=f'{symbol} equ ${sy[symbol]:x}\n'
target.with_suffix('.s').write_text(src+lookup+'\n')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(target.with_suffix('.bin')),str(target.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
patches.extend([(private,target.with_suffix('.bin').read_bytes()),(lay['code_base']+0xb696,bytes.fromhex('4eb9')+struct.pack('>I',private))])
# The phase build leaves B856's original root call and stack cleanup intact.
patches.append((lay['code_base']+0xb856,bytes.fromhex('4eac81be584f')))
patches.append((lay['code_base']+0x9564,Path('tmp/p4-native-root.bin').read_bytes()))
for index,h in enumerate(handles):
 for name,addr in [('chip',0),('slow',0xc00000)]:write(addr,(root/f'timing-state-{name}.bin').read_bytes())
 # Only the private audio body is a counter. Native pitch computation and the
 # slave's last-segment audio gate still execute unchanged.
 write(a4-0x7fe0,bytes.fromhex('4ef900042000'));write(0x42000,bytes.fromhex('52b9000430004e75'))
 write(stop,bytes.fromhex('40f900043004'))
 if index:
  for addr,body in patches:write(addr,body)
saved_data=read(lay['data_base'],31948);rng=random.Random(40429)
def invoke(name):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,sy[name],stop,1000000,40000));assert reg(18)==stop and reg(8)==sp+4
counts={'active':0,'inactive':0}
try:
 for case in range(6000):
  phase_index=rng.randrange(8);n=rng.randint(1,8-phase_index);gear=rng.randint(1,4);av=rng.randrange(1900*8)*8192;ar=rng.randrange(6500*8)*8192;active=case%10!=0
  cv=av if phase_index==0 else rng.randrange(1900*64)*1024;cr=ar if phase_index==0 else rng.randrange(6500*64)*1024
  inputs=[(0x991c,rng.randrange(101)),(0x9910,15),(0x993e,1),(0x9606,0),(0xe94a,rng.choice([0,255])),(0xaf31,rng.choice([0,255])),(0xf790,rng.choice([0,255])),(0xf791,rng.choice([0,255])),(0xaddc,rng.choice([0,255]))]
  brake=rng.choice([0,255]);pitch=rng.randint(-16384,16384);thcarry=rng.randint(-65535,65535);last_segment=rng.choice([1,2]);outputs=[]
  for h in handles:
   write(lay['data_base'],saved_data);write(ph,bytes(78));write(ss,bytes(16));write(dt,bytes(16));write(sy['_phase_speed_cache'],bytes(8));write(sy['_drivetrain_power_state'],bytes(24));write(sy['_drivetrain_sqrt_state'],bytes(20));write(0x43000,bytes(6))
   for k in range(1,17):reg(k,k*0x10101)
   reg(17,0x2010 if case%2 else 0x2000);reg(5,a4);reg(7,ph)
   for off,fmt,v in [(0,'H',1),(2,'H',int(active)),(4,'H',phase_index),(6,'H',n),(8,'H',n),(10,'H',n),(12,'I',av),(16,'I',cv),(20,'I',ar),(24,'I',cr),(32,'H',gear),(72,'H',brake),(74,'H',8-phase_index)]:pack(ph+off,fmt,v)
   for off,v in inputs:write(a4+off-65536,bytes([v]))
   pack(a4-0x6bb4,'h',pitch);pack(a4-0x66c0,'I',0x44000+8*gear);pack(dt,'HHHH',n,last_segment,0,1);pack(ss+4,'i',thcarry);write(ss+8,read(a4-0x66e4,1))
   invoke('_phase_prepare_anchor')
   reg(17,0x2010 if case%2 else 0x2000)
   preserved={k:reg(k) for k in [4,5,6,7,13,14,15,16]}
   invoke('_phase_engine_call');assert all(reg(k)==v for k,v in preserved.items()),(case,'preserved register')
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1))
   outputs.append([read(lay['data_base'],31948),read(ph,78),(read(ss+4,6) if active else read(ss,16)),read(dt,16),read(0x43000,6)])
  assert outputs[0]==outputs[1],(case,[(j,[(k,x,y) for k,(x,y) in enumerate(zip(a,b)) if x!=y][:8]) for j,(a,b) in enumerate(zip(*outputs)) if a!=b])
  counts['active' if active else 'inactive']+=1
 report=dict(passed=True,cases=6000,paths=counts,exact=['all native globals','phase state and live scalar companions; active V/R stores delayed to final publication','drivetrain state','pure implementation memo bookkeeping excluded','audio pitch and call count','callee-saved registers','stack','materialized SR'],scope='Separate 68000 emulator instances, old and new phase/scalar hooks inside the actual patched native engine. D1-D3/A0 dead engine scratch are intentionally not compared; phase_frame preserves D2-D3, while D1/A0 are native caller scratch.')
 Path('tmp/p4-root-engine-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:
 for h in handles:ok(u.uc_close(h))
