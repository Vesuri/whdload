import os,sys,json
from pathlib import Path
import replay_flight as r
from baseline_matrix import VARIANTS
from amigaxdev import barto
os.chdir(r.ROOT);out=Path(sys.argv[1]).resolve()
def observer(cmd,dump,bases,hs,out):
 def shot(n):
  p=out/(str(n)+'.trace');cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(out/(str(n)+'.png')).write_bytes(t.fields[-1].shot)
 shot('initial')
 for n,k in enumerate([0x20,0x44,0x35,0x44,0x33,0x44,0x44,0x44,0x44]):
  cmd(f'monitor key {k:x} 1');cmd('monitor fields 40');cmd(f'monitor key {k:x} 0');cmd('monitor fields 80');shot(n)
source=Path(r.__file__).read_text().replace("  for i,k in enumerate(tape['enrolment']):", "  observer(cmd,dump,bases,hs,out);return {}\n  for i,k in enumerate(tape['enrolment']):").replace("dump('locate-fast.bin',0x40000000,0x2000000)","dump('locate-fast.bin',0x41a00000,0x400000)").replace('fast[a-0x40000000:a-0x40000000+n]','fast[a-0x41a00000:a-0x41a00000+n]').replace('0x40000000+pos-off','0x41a00000+pos-off')
ns=dict(r.__dict__);ns['__name__']='probe';exec(compile(source,r.__file__,'exec'),ns)
ns['run']('020',out,Path(str(out)+'-seed'),observer,dict(VARIANTS['original'],custom3=0))
