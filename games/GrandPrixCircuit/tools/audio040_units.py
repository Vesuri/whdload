"""Execute assembled music helpers in Unicorn; model custom-register semantics.
This is an instruction/interrupt-order test, not Paula timing emulation.
"""
from pathlib import Path
import ctypes as C,re,struct,json
root=Path(__file__).resolve().parents[1];out=root/'tmp/audio040'
u=C.CDLL(str(Path.home()/'.local/share/amiga/unicorn/lib/libunicorn.2.dylib'))
for name,args in {'uc_open':[C.c_int,C.c_int,C.POINTER(C.c_void_p)],'uc_ctl':[C.c_void_p,C.c_int],'uc_mem_map':[C.c_void_p,C.c_uint64,C.c_size_t,C.c_uint32],'uc_mem_write':[C.c_void_p,C.c_uint64,C.c_void_p,C.c_size_t],'uc_mem_read':[C.c_void_p,C.c_uint64,C.c_void_p,C.c_size_t],'uc_reg_write':[C.c_void_p,C.c_int,C.c_void_p],'uc_reg_read':[C.c_void_p,C.c_int,C.c_void_p],'uc_emu_start':[C.c_void_p,C.c_uint64,C.c_uint64,C.c_uint64,C.c_size_t],'uc_close':[C.c_void_p]}.items():getattr(u,name).argtypes=args
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
def ok(n):assert n==0,n
def run(variant,wrapper,mask=1,pitch=False,effect=False,active=False):
 h=C.c_void_p();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,7|(1<<26)|(1<<30),C.c_int(4)));ok(u.uc_mem_map(h,0,0x1000000,7))
 def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
 def word(a,v):write(a,struct.pack('>H',v&65535))
 def long(a,v):write(a,struct.pack('>I',v))
 def reg(r,v=None):
  x=C.c_uint32(v or 0)
  if v is None:ok(u.uc_reg_read(h,r,C.byref(x)));return x.value
  ok(u.uc_reg_write(h,r,C.byref(x)))
 folder=out/('build-'+variant);data=(folder/'GrandPrixCircuit.slave').read_bytes();text=(folder/'GrandPrixCircuit.slave.lst').read_text(encoding='latin1')
 sym=lambda n:0x10000+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',text,re.M)[1],16)
 size=struct.unpack_from('>I',data,28)[0]*4;write(0x10000,data[32:32+size]);long(sym('h0_end_address'),0x20000);long(sym('lab62_address'),0x20002);word(0x20000,mask);word(0x20002,mask);word(0x20004,0x8080)
 state={'ena':0x780,'req':0x780,'dma':15 if not mask&0x8000 or active else 0};events=[]
 CB=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
 def onwrite(uc,typ,a,n,v,user):
  v &= (1 << (n*8))-1
  if a in (0xdff09a,0xdff09c,0xdff096):
   key={0xdff09a:'ena',0xdff09c:'req',0xdff096:'dma'}[a];bits=v&0x7fff;state[key]=(state[key]|bits) if v&0x8000 else state[key]&~bits;events.append((key,v))
 cb=CB(onwrite);handle=C.c_size_t();ok(u.uc_hook_add(h,C.byref(handle),1<<11,cb,None,0xdff096,0xdff09d))
 reg(17,0x2000);reg(8,0x40000);reg(9,0x12345678);reg(10,0xabcdef01);reg(11,mask);reg(16,mask);reg(4,0x21000);reg(1,0x23000);long(0x21030,0xdff0a0)
 stop=0x31000;long(0x40000,stop);pc=sym(wrapper);injected=False
 if pitch:
  # Original JSR $802 / TST D3 and new hook at $758, with a pitch writer
  # standing in for the table lookup. Inject the old-note completion precisely
  # after it, before the old $776 protection. Native handler writes VOL=0/PER=124.
  pc=0x30000+0x758;stop=0x30000+0x77c
  write(0x30000+0x802,bytes.fromhex('33fc019000dff0a64e75'))
  word(0x21046,1 if effect else 0);reg(12,0);word(0x2101e,32)
  if variant=='before':write(pc,bytes.fromhex('4eba00a84a43'))
  else:write(pc,b'\x4e\xb9'+struct.pack('>I',sym('music_note_begin')))
  write(0x30000+0x75e,bytes.fromhex('4e71')*12)
  write(0x30000+0x776,(b'\x4e\xb9'+struct.pack('>I',sym('music_note_begin'))) if variant=='before' else bytes.fromhex('2c6b00302c88'))
 for i in range(2000):
  word(0xdff002,state['dma']);word(0xdff006,(i&255)<<8);word(0xdff01c,state['ena']);word(0xdff01e,state['req'])
  if pitch and pc==0x3075e and state['ena']&0x80:
   word(0xdff0a6,124);word(0xdff0a8,0);injected=True
  if pc==stop or (not pitch and pc==stop+({'move_f_dmacon':2,'move_h0_end_dmacon':4,'move_lab62_dmacon':4}.get(wrapper,0))):break
  ok(u.uc_emu_start(h,pc,0xffffff,0,1));pc=reg(18)
 else:raise AssertionError('helper did not return')
 if pitch:
  b=C.create_string_buffer(2);ok(u.uc_mem_read(h,0xdff0a6,b,2));result={'period':int.from_bytes(b.raw,'big'),'old_completion_delivered':injected,'interrupt_mask':state['ena']}
 else:
  assert reg(9)==0x12345678 and reg(10)==0xabcdef01 and reg(8)==0x40004
  result={'state':state,'events':events}
 ok(u.uc_close(h));return result
before=run('before','music_note_begin',pitch=True);after=run('candidate','music_note_begin',pitch=True)
assert before['period']==124 and after['period']==400,(before,after)
effect=run('candidate','music_note_begin',pitch=True,effect=True)
assert effect['interrupt_mask']==0x780, effect
cases=0
for mask in (1,2,4,8,15):
 for wrapper in ('move_d2_dmacon','move_d7_dmacon','move_lab62_dmacon'):
  r=run('candidate',wrapper,mask);assert r['state']['ena']==0x780&~(mask<<7) and r['state']['dma']==15&~mask;cases+=1
 r=run('candidate','move_h0_end_dmacon',mask|0x8000);assert r['state']['req']==0x780&~(mask<<7) and r['events'][-1]==('dma',mask|0x8000);cases+=1
r=run('candidate','move_f_dmacon');assert r['state']['ena']==0 and r['state']['dma']==0;cases+=1
active=run('candidate','move_h0_end_dmacon',0x800f,active=True)
assert active['state']['req']==0x780,active
report={'active_effect_request_preserved':True,'pitch_interruption_before':before,'pitch_interruption_after':after,'effect_interrupts_preserved':True,'dma_helper_cases':cases,'scope':'Assembled instruction execution with modeled registers, not physical Paula timing.'};(out/'unit-results.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
