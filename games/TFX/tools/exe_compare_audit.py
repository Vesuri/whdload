"""Read-only gates for the shared tfx.020 renderer and CPU-specific helpers."""
import re,json
from pathlib import Path

def audit(cmd,dump,bases,hs,out,machine,v,listing):
 sym={n:int(a,16) for n,a in re.findall(r'^(\S+)\s+00:([0-9A-Fa-f]+)\s*$',Path(listing).read_text(encoding='latin1'),re.M)}
 b=bases[0];code=dump('renderer-code.bin',b,hs[0]['size'])
 # Joystick correctness hook exists with original rendering and FPS disabled too.
 assert code[0x41054:0x41056]==bytes.fromhex('4eb9')
 sb=int.from_bytes(code[0x41056:0x4105a],'big')-sym['test_fire']
 jmp=lambda n:bytes.fromhex('4ef9')+(sb+sym[n]).to_bytes(4,'big')
 info=cmd('monitor cpuinfo');fields=dict(re.findall(r'(\w+)=(\w+)',info))
 assert int(fields['cpu'])==int('68'+machine)
 assert int(fields['fpu'])=={'020':68881 if '--uae_fpu_model=68881' in v.get('extra_args','') else 68882,'030':68882,'040':68040,'060':68060}[machine]
 enabled=not bool(v['custom4']&4)
 assert all(a>=0x40000000 if enabled else a<0x200000 for a in bases[1:])
 for off,name in [(0x4f840,'gouraud_runs'),(0x4f9f8,'texture_fill'),(0x4e400,'mask_sprite8_040'),(0x249a,'fade_cols_040'),(0x6c514,'sfd_span_040'),(0x4bdca,'isqrt_040')]:
  assert (code[off:off+6]==jmp(name))==enabled,(hex(off),name)
 rot=enabled and machine=='040'
 assert code[0x59748:0x5974e]==(jmp('rot_delta2_040') if rot else bytes.fromhex('4c9800032604'))
 pointers={}
 for name,want in [('rot_table',rot),('delta_shadow',enabled and machine!='020')]:
  a=sb+sym[name];cmd(f'monitor tfxsync {a:x} 4');ptr=int.from_bytes(dump(name+'.bin',a,4),'big');assert bool(ptr)==want,(name,ptr,want);pointers[name]=ptr
 project=enabled and not v.get('custom5',0)
 assert (code[0x55e32:0x55e38]==jmp('project_int_040' if v.get('custom1',0) else 'project_fpu_040'))==project
 # Full 040 alone gets native transcendental slots. 6888x keep native opcodes;
 # 060 retains the existing emulation list, applied after the render list.
 assert (code[0x51682:0x51686]==bytes.fromhex('4eb80220'))==(machine=='040' and not v.get('custom5',0))
 meta=json.loads((Path(__file__).resolve().parents[1]/'tmp/step9/fpu-sites.json').read_text())
 offsets=[x['offset'] for x in meta['sites']]+[0x50f82,0x51682,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]
 if machine=='060' and not v.get('custom5',0):
  old=(Path(__file__).resolve().parents[1]/'tmp/step13/candidate-060/060-newfpu/code.bin').read_bytes()
  assert all(code[o:o+4]==old[o:o+4] for o in offsets),'060 FPU sites changed'
 if machine in ['020','030'] or v.get('custom5',0):
  assert all(code[o:o+4]==hs[0]['bytes'][o:o+4] for o in offsets),'original FPU sites changed'
 (out/'renderer-audit.json').write_text(json.dumps(dict(passed=True,machine=machine,enabled=enabled,rotation=rot,project=project,pointers=pointers,cpu=fields),indent=2))
