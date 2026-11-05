import ctypes as C,json,os,random,re,struct,subprocess
from pathlib import Path
exec(Path('tools/check_record_equal_micro.py').read_text().split('for addr,name in ')[0])
source=Path('src/HardDrivinRecord.s').read_text();interp=source[source.index('_record_copy:'):source.index('\n\tIFD VERIFY_RECORD_MATH',source.index('_record_copy:'))];defer=source[source.index('_record_defer:'):source.index('_record_rewind:')]
state=source[source.index('_record_pending:'):source.index('_record_reset:')]
reset=source[source.index('_record_reset:'):source.index('_record_native:')]
stem=Path('tmp/p2-pending');stem.with_suffix('.s').write_text(' org $10000\n'+reset+defer+interp+'\n'+state)

subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)};write(0x10000,stem.with_suffix('.bin').read_bytes())
pack(sy['_record_pending'],'I',0x30000);pack(sy['_record_pending_write'],'I',0x30000);pack(sy['_record_pair_write'],'I',0x302d0)
stop=0x18000;sp=0x4fff0;ring=0x20000;a4=ring+0x4e6e;leftaddr=0x28000;rightaddr=0x29000;expected=bytearray(14220);write(ring,bytes(expected));write(0x30000,bytes(29476));rng=random.Random(20)
def invoke(name):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,sy[name],stop,10000000,200000));assert reg(8)==sp+4
resolves=0
for case in range(10000):
 den=rng.choice([1,8,13,16,255,256,32768,65535,rng.randint(1,65535)]);num=rng.randint(1,den)
 left=[];right=[]
 for j in range(79):
  kind=('uusaaap'[j] if j<7 else 'usuaaa'[(j-7)%6])
  x=rng.randint(-720,720)&65535 if kind=='a' else rng.randrange(65536);y=rng.randint(-720,720)&65535 if kind=='a' else rng.randrange(65536)
  if rng.random()<.4:y=x
  left.append(x);right.append(y)
 slot=case%90;dest=ring+158*slot
 write(leftaddr,struct.pack('>79H',*left));write(rightaddr,struct.pack('>79H',*right));reg(17,0x2000);reg(1,leftaddr);reg(2,rightaddr);reg(3,dest);reg(4,0x28100);reg(5,a4);reg(11,num);reg(15,den);reg(16,case)
 pack(sy['_record_pending_write'],'I',0x30000+slot*8);pack(sy['_record_pair_origin'],'I',0);pack(sy['_record_pair_saved'],'H',0);invoke('_record_defer');assert reg(4)==0x28100 and reg(5)==a4 and reg(11)==num and reg(15)==den and reg(16)==case
 expected[slot*158:(slot+1)*158]=struct.pack('>79H',*blend(left,right,num,den))
 if case%131==0 or case==9999:
  saved={k:reg(k) for k in range(1,17) if k!=8};invoke('_record_resolve');assert all(reg(k)==v for k,v in saved.items());assert read(ring,14220)==expected,case
  assert all(read(0x30000+j*8,4)==b'\0'*4 for j in range(90));resolves+=1
# Multiple outputs share one pair; replacements reuse that pair and origin.
slot=0;shared_records=0;replacements=0
for transaction in range(2000):
 count=rng.choice([1,1,2,2,3,4,91]);den=8*count+rng.randrange(8);origin=slot
 pack(sy['_record_pair_origin'],'I',0)
 for replacement in range(2 if transaction%4==0 else 1):
  replacements+=bool(replacement);pack(sy['_record_pair_saved'],'H',0)
  left=[rng.randrange(65536) if ('uusaaap'[j] if j<7 else 'usuaaa'[(j-7)%6])!='a' else rng.randint(-720,720)&65535 for j in range(79)]
  right=[rng.randrange(65536) if ('uusaaap'[j] if j<7 else 'usuaaa'[(j-7)%6])!='a' else rng.randint(-720,720)&65535 for j in range(79)]
  write(leftaddr,struct.pack('>79H',*left));write(rightaddr,struct.pack('>79H',*right))
  slot=origin
  for j in range(count):
   num=(j+1)*8;reg(1,leftaddr);reg(2,rightaddr);reg(3,ring+158*slot);reg(4,0x28100);reg(5,a4);reg(11,num);reg(15,den);reg(16,j)
   pack(sy['_record_pending_write'],'I',0x30000+slot*8);invoke('_record_defer')
   expected[slot*158:(slot+1)*158]=struct.pack('>79H',*blend(left,right,num,den));slot=(slot+1)%90;shared_records+=1
 if transaction%133==0 or transaction==1999:
  invoke('_record_resolve');assert read(ring,14220)==expected,('shared',transaction);resolves+=1
# Allocation failure retains eager exact interpolation.
pack(sy['_record_pending'],'I',0);reg(1,leftaddr);reg(2,rightaddr);reg(3,ring);invoke('_record_defer');assert read(ring,158)==struct.pack('>79H',*blend(left,right,num,den))
# Reset resolves pending tail bytes, clears descriptors and preserves incoming X.
for x in [0,1]:
 pack(sy['_record_pending'],'I',0x30000);pack(sy['_record_pending_write'],'I',0x30000);pack(sy['_record_pair_origin'],'I',0);pack(sy['_record_pair_saved'],'H',0)
 reg(1,leftaddr);reg(2,rightaddr);reg(3,ring);reg(5,a4);reg(11,num);reg(15,den);invoke('_record_defer');expected[:158]=struct.pack('>79H',*blend(left,right,num,den))
 write(sy['_record_state'],b'X'*32);reg(17,0x2000|(x<<4));reg(9,0xdeadbeef);reg(2,0x12345678)
 invoke('_record_reset');assert read(ring,14220)==expected;assert read(sy['_record_state'],32)==bytes(32);assert reg(9)==0xdeadbeef and reg(2)==0x12345678 and reg(1)==ring;write(stop,bytes.fromhex('40f900042000'));ok(u.uc_emu_start(h,stop,stop+6,1000000,10));assert read(0x42000,2)[1]&31==x<<4
 assert all(read(0x30000+j*8,4)==bytes(4) for j in range(90));assert read(a4-0x16e2,4)==struct.pack('>I',ring)
report=dict(passed=True,assembled_68000_records=10000,full_ring_resolutions=resolves,shared_transactions=2000,shared_records=shared_records,replacement_transactions=replacements,words=790000+shared_records*79,ring_wrap_and_replacement=True,allocation_failure_fallback=True,preserved_resolver_registers=True,reset_tail_and_x_cases=2)
Path('tmp/p2-pending.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
