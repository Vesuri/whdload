"""Compare assembled old/new dispatcher boundaries, including native-entry CCR."""
from pathlib import Path
import re,struct,random,json,os,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
r=Path('src');old=Path('tmp/p5-before');symbols=[]
for idx,root in enumerate([old,r]):
 d=(root/'HardDrivinDispatch.s').read_text();t=(root/'HardDrivinTime.s').read_text();ev=(r/'HardDrivinEvents.s').read_text()
 equ='\n'.join(l for l in (d+'\n'+t).splitlines() if re.match(r'(DS_|TS_|TIME_).* equ ',l))+'\n'
 block=d[d.index('_dispatch_begin:'):d.index('\n\tINCLUDE "HardDrivinEvents.s"')]
 motion=(root/'HardDrivinMotion.s').read_text()
 crash=motion[motion.index('_motion_crash_tick:'):motion.index('_motion_crash_signature:')]
 replay=t[t.index('_time_replay_call:'):t.index('; Published diagnostic block')]
 outer=t[t.index('_time_outer:'):t.index('\n\tIFD VERIFY_TIME_SCALARS\n; Cache')]
 take=t[t.index('_time_take_fields:'):t.index('\n\tIFD VERIFY_TIME_MATH\n;',t.index('_time_take_fields:'))]
 events=ev[ev.index('_events_begin_step:'):ev.index('; A0 slot')]
 src=f' org ${0x2c000+idx*0x1000:x}\nVERIFY_TIME_DISPATCH equ 1\nVERIFY_DISPATCH_CPU equ 1\nVERIFY_TIME_SCALARS equ 1\nVERIFY_TIME_PRESENTATION equ 1\n'+equ
 src+='''_dispatch_state equ $30000
_time_state equ $30100
_time_scalar_fields equ $30200
_events_score_state equ $30300
_dispatch_cpu_single equ $30400
_dispatch_cpu_oversized equ $30404
_motion_crash_state equ $30310
_presentation_recovery equ $30320
'''
 src+=outer+block+take+events+crash+replay+'''
_time_reset_scalars:
 addq.l #1,$30500
 rts
_time_prepare_constants:
 moveq #0,d0
 moveq #1,d1
 rts
_time_throttle_up:
_time_throttle_down:
_time_expired_throttle:
 rts
_code_start: dc.l $80000
_dispatch_recovery_ptr: dc.l $908a2
_dispatch_scene_ptr: dc.l $8e706
'''
 stem=Path(f'tmp/p5-dispatch-{idx}');stem.with_suffix('.s').write_text(src)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 write(0x2c000+idx*0x1000,stem.with_suffix('.bin').read_bytes());symbols.append({n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)})
a4=0x70000;stop=0x60000;sp=0x5f000
# Stubs materialize the actual incoming CCR, so no lazy-SR comparison.
for addr in [stop,0x90edc,0x90f5e,0x87dea,0x8e706,0x908a2]:write(addr,bytes.fromhex('40f9000306004e71'))
write(a4-0x7fec,bytes.fromhex('40f9000306024e75'))
write(0x90b08,bytes.fromhex('4e55ffe648e70f304a2cadd766084cdf0cf04e5d4e75'))
# The recovery body is unchanged; exercise its actual inactive prologue/gate
# and count entry to its active continuation.
stem=Path('tmp/p5-recovery-stub');stem.with_suffix('.s').write_text(""" org $908a2
 link a5,#-4
 movem.l d4/a2,-(a7)
 tst.b -$69fb(a4)
 bne.s .active
 move.l a0,-(a7)
 lea $30320,a0
 clr.l (a0)
 movea.l (a7)+,a0
 tst.b -$69fb(a4)
 bra.s .exit
.active:
 addq.l #1,$30324
.exit:
 movem.l (a7)+,d4/a2
 unlk a5
 rts
""")
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x908a2,stem.with_suffix('.bin').read_bytes());write(a4-0x7e7e,bytes.fromhex('7025720b4e75'))
rng=random.Random(505);counts={};endpoints=[stop,0x90edc,0x90f5e,0x87dea,0x8e706]
try:
 for name in ['_dispatch_begin','_dispatch_take','_dispatch_latch','_dispatch_steering','_dispatch_after_physics','_time_outer','_motion_crash_tick','_time_replay_call','_dispatch_controls']:
  for case in range(2400):
   n=rng.choice([0,1,7,8,9,32,65535,65536,0xffffffff,rng.randrange(100000)])
   state=bytearray(rng.randbytes(0x700));struct.pack_into('>I',state,0,n);state[24]=rng.choice([0,255]);state[25]=rng.choice([0,255]);struct.pack_into('>H',state,0x400,case%2)
   fields=rng.randrange(1<<32);previous=(fields-n)&0xffffffff
   struct.pack_into('>II',state,0x100,fields,previous);state[0x11c]=rng.choice([0,255])
   if case%2==0:state[0x310:0x314]=bytes(4)
   crash_value=0 if case%2==0 else rng.randrange(256)
   regs=[rng.randrange(1<<32) for k in range(17)];sr=0x2000|(case%32);race=rng.choice([0,1,255]);buttons=rng.choice([0,1,4,65535]);mouse=rng.randrange(65536);outs=[]
   for sy in symbols:
    write(a4-0x69fb,bytes([case%3]));write(a4-0x69fa,bytes([crash_value]));write(a4-0x5229,bytes([0]));write(0x30000,bytes(state));write(a4-0x522c,bytes([race]));pack(a4-0x6a0a,'H',buttons);pack(a4-0x6a06,'H',mouse)
    reg(17,sr)
    for k in range(1,17):reg(k,regs[k])
    reg(5,a4);reg(8,sp);pack(sp,'I',stop)
    if name=='_dispatch_begin':reg(9,n)
    if name=='_dispatch_take':reg(1,0x30000)
    pc=sy[name]
    # Step until any one of the native continuations, then materialize CCR.
    for count in range(500):
     ok(u.uc_emu_start(h,pc,0,1000000,1));pc=reg(18)
     if pc in endpoints:break
    else:raise AssertionError((name,case,hex(pc)))
    ok(u.uc_emu_start(h,pc,pc+6,1000000,1))
    outs.append((pc,[reg(k) for k in range(1,17)],read(0x30000,0x700)+read(a4-0x69fa,1)))
   assert outs[0]==outs[1],(name,case,n,race,sr,[(j,a,b) for j,(a,b) in enumerate(zip(outs[0][1],outs[1][1])) if a!=b],[(i,x,y) for i,(x,y) in enumerate(zip(outs[0][2],outs[1][2])) if x!=y][:15])
  counts[name]=2400
 report=dict(passed=True,cases=counts,total=sum(counts.values()),checks=['all D/A registers','stack and destination','materialized CCR at continuations and native wait','time/dispatch/event/scalar state','both CPU policies','zero and unsigned overflow intervals','active/inactive and race exit'])
 Path('tmp/p5-recovery-boundaries-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
