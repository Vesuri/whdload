"""Read-only audit of CPU gates, original-rendering opt-out and combined options."""
import sys,os,json,struct
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();cpu=sys.argv[2];c4=int(sys.argv[3]);os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 code=dump('code.bin',bases[0],hs[0]['size']);target=cpu=='040';original=bool(c4&4)
 assert struct.unpack_from('>H',code,0x1abfe)[0]==(0x7001 if target else 0x7002)
 for o in [0x1830,0x1850,0x1ec38,0x1fec4]:assert (code[o:o+2]==bytes.fromhex('4eb9'))==target
 for o in [0x4f840,0x4f9f8]:assert (code[o:o+2]==bytes.fromhex('4ef9'))==(target and not original)
 # The original opt-out must use the actual game routines, including blitter lines.
 if original:
  for o in [0x4de00,0x500dc,0x4dba0,0x4dbc8]:assert code[o:o+6]==hs[0]['bytes'][o:o+6]
 assert (bases[1]>=0x40000000 and bases[2]>=0x40000000)==(target and not original)
 (out/'audit.json').write_text(json.dumps(dict(cpu=cpu,custom4=c4,limit=hex(struct.unpack_from('>H',code,0x1abfe)[0]),new_helpers=target,original_rendering=original,passed=True),indent=2))
 print(cpu,c4,'gate audit passed',flush=True)
v=dict(executable='tfx.020',custom3=3,custom4=c4,swap=0x19fc,extra_args='--uae_fpu_no_unimplemented=true' if cpu=='040' else '')
run(cpu,out,Path(str(out)+'-seed'),capture,v)
