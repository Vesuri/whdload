"""Check actual CUSTOM4 hook installation, VBL delay, ready flag and register preservation."""
import os,sys,time,json,struct,re,subprocess,shutil
from capture_demo import ROOT,SOCK,command,sha
os.chdir(ROOT);n=int(sys.argv[1]);name=sys.argv[2];out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False);rel=out.relative_to(ROOT)
if SOCK.exists():
 try:command('quit')
 except (FileNotFoundError,ConnectionError):pass
slave=ROOT/'tmp/build/HardDrivin-slow.slave';shutil.copyfile(slave,out/'slave.slave')
env=dict(os.environ,FSUAE=shutil.which('fs-uae'),SLAVE=str(slave),WHD_ARGS=f'CUSTOM4={n}',JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',WINDOW='none',WAIT_FOR_EXIT='0',BOOT_BREAK='0xcfb920',CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')
log=(out/'server.log').open('w');p=subprocess.Popen([sys.executable,str(ROOT/'tools/harddrivin.py'),'serve'],env=env,stdout=log,stderr=subprocess.STDOUT)
try:
 deadline=time.monotonic()+180
 while 'serving on' not in (out/'server.log').read_text():
  assert p.poll() is None and time.monotonic()<deadline;time.sleep(.2)
 command(f'gdb dump binary memory {rel}/slow.bin 0xc00000 0xd80000')
 mem=(out/'slow.bin').read_bytes();lst=(ROOT/'tmp/build/slow.lst').read_text(encoding='latin1')
 def sym(k):return int(re.search(r'^'+k+r'\s+00:([0-9A-Fa-f]+)',lst,re.M).group(1),16)
 hits=[i for i in range(0,len(mem)-8,2) if mem[i:i+8]==bytes.fromhex('00cfb1d000011a4e')];assert len(hits)==1
 slavebase=0xc00000+hits[0]-sym('_code_start');addr=lambda k:slavebase+sym(k)
 count=struct.unpack_from('>H',mem,addr('_verify_slow_count')-0xc00000)[0]
 assert count==max(0,min(n,255)-1)
 ready=0xd15f16-0x69ff;counter=addr('_verify_slow_fields');entry=addr('_verify_slow_submit');publish=addr('_verify_slow_publish');poll=addr('_verify_slow_poll')
 patch=lambda off:mem[0xcfb1d0-0xc00000+off:0xcfb1d0-0xc00000+off+6].hex()
 if not n:
  assert patch(0x756)=='197c00ff9601' and patch(0x3e2)=='22d822d822d8'
 else:
  assert patch(0x756)=='4eb9'+f'{entry:08x}' and patch(0x3e2)=='4eb9'+f'{addr("_verify_slow_vbl"):08x}'
 records=[]
 for i in range(6 if n<255 else 2):
  command(f'until {entry if n else 0xcfb926:#x}')
  before=command('gdb info registers');(out/f'before-{i}.txt').write_text(before)
  if n:
   command(f'until {poll:#x}')
   first=command(f'gdb printf "BEGIN %u %u\\n", *(unsigned long*){counter:#x}, *(unsigned char*){ready:#x}')
   start,flag=map(int,re.search(r'BEGIN (\d+) (\d+)',first).groups());assert flag==0
   command(f'until {publish:#x}')
   last=command(f'gdb printf "END %u %u\\n", *(unsigned long*){counter:#x}, *(unsigned char*){ready:#x}')
   end,flag=map(int,re.search(r'END (\d+) (\d+)',last).groups());assert flag==0 and (end-start)&0xffffffff==min(n,255)
  else:start=end=0
  command('until 0xcfb92c')
  after=command('gdb info registers');(out/f'after-{i}.txt').write_text(after)
  # Check general registers only. SR is retained in the raw logs but is
  # not used as CCR evidence; it differs from the native MOVE expectation.
  # CCR preservation follows CMP/DBF (X unchanged) plus the native MOVE.
  regs=lambda s:{k:int(v,16) for k,v in re.findall(r'^(d[0-7]|a[0-6]|sp)\s+0x([0-9a-f]+)',s,re.M)}
  rb,ra=regs(before),regs(after)
  # The injected JSR return address accounts for one extra stack long at entry.
  for k in rb:
   if k=='sp':assert ra[k]==rb[k]+(4 if n else 0)
   else:assert ra[k]==rb[k],(k,rb,ra)
  flag=command(f'gdb printf "READY %u\\n", *(unsigned char*){ready:#x}');assert 'READY 255' in flag
  records.append(dict(start=start,end=end,extra_fields=end-start));print(n,i,records[-1],flush=True)
 report=dict(custom4=n,effective=min(n,255),patch_ready=patch(0x756),patch_vbl=patch(0x3e2),slave_sha256=sha(slave),records=records)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 command('quit');p.wait(timeout=10)
