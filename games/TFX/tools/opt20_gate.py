"""Live CPU/render-option gates for delta-copy allocation and PlayLevel hook."""
import os,sys,json,re
from pathlib import Path
import replay_flight as replay
from replay_flight import ROOT
source=Path(replay.__file__).read_text().replace("cmd('monitor fields 1500');print", "\n  for _ in range(6):cmd('monitor fields 250')\n  print")
namespace=dict(replay.__dict__);namespace['__name__']='opt20_gate_boot'
exec(compile(source,replay.__file__,'exec'),namespace)
run=namespace['run']
from baseline_matrix import VARIANTS,observer
root=Path(sys.argv[1]).resolve();machine=sys.argv[2];original=len(sys.argv)>3 and sys.argv[3]=='original';os.chdir(ROOT)
listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
def offset(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
v=dict(VARIANTS['integer' if machine=='020' else 'newfpu'],custom4=30 if original else 18,extra_args='--uae_fpu_no_unimplemented=true')
if machine=='040':v['extra_args']+=' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'
v['custom5']=int(os.environ.get('CUSTOM5','0'));v['custom1']=int(os.environ.get('CUSTOM1','0'))
def capture(cmd,dump,bases,hs,out):
 b=bases[0];sb=int.from_bytes(dump('swap-target.bin',b+v['swap']+2,4),'big')-offset('do_swap_screen')
 ptr=int.from_bytes(dump('delta-pointer.bin',sb+offset('delta_shadow'),4),'big');enabled=machine=='040' and not original
 assert bool(ptr)==enabled,(machine,original,hex(ptr))
 hook=None
 if machine!='020':
  raw=dump('play-entry.bin',b+0x16de,6);hook=raw.hex()
  assert hs[0]['bytes'][0x16de:0x16e4].hex()=='f22769002f02'
  if enabled:assert raw==bytes.fromhex('4ef9')+(sb+offset('reset_copy_shadows')).to_bytes(4,'big')
  else:assert raw==hs[0]['bytes'][0x16de:0x16e4]
 edge=None
 if machine!='020':
  edge=dump('edge-entry.bin',b+0x6c534,12).hex()
  assert edge==('e9c136c578209843e9c256c5' if machine=='040' and not original else hs[0]['bytes'][0x6c534:0x6c540].hex()),edge
 project=None
 if machine!='020':
  project=dump('project-entry.bin',b+0x55e32,6).hex()
  active=machine=='040' and not original and not v['custom5']
  expected=(bytes.fromhex('4ef9')+(sb+offset('project_int_040' if v['custom1'] else 'project_fpu_040')).to_bytes(4,'big')) if active else hs[0]['bytes'][0x55e32:0x55e38]
  assert project==expected.hex(),project
 exp=None
 if machine!='020':
  exp=dump('exp-entry.bin',b+0x51682,4).hex()
  assert exp==('4eb80220' if machine=='040' and not v['custom5'] else 'f2001c10'),exp
 mask=None
 if machine!='020':
  mask=dump('mask-entry.bin',b+0x4e400,6).hex()
  # Unpatched: MOVEQ #7,D0 / MOVE.L A1,abs (relocated high word of $4e52a).
  expected=(bytes.fromhex('4ef9')+(sb+offset('mask_sprite8_040')).to_bytes(4,'big')) if enabled else bytes.fromhex('700723c9')+(b+0x4e52a).to_bytes(4,'big')[:2]
  assert mask==expected.hex(),mask
 fade=None
 if machine!='020':
  fade=dump('fade-entry.bin',b+0x249a,6).hex()
  assert hs[0]['bytes'][0x249a:0x24a0].hex()=='594f48e73f34'
  # Step 7: only a slave that has fade_cols_040 patches @AltFadeColsMiss.
  palette=enabled and re.search(r'^fade_cols_040\s',listing,re.M) is not None
  assert fade==((bytes.fromhex('4ef9')+(sb+offset('fade_cols_040')).to_bytes(4,'big')) if palette else hs[0]['bytes'][0x249a:0x24a0]).hex(),fade
 rot=None
 if machine!='020':
  rot=dump('rot-entry.bin',b+0x59748,6).hex()
  assert hs[0]['bytes'][0x59748:0x5974e].hex()=='4c9800032604'
  # Step 8: only a slave that has rot_delta2_040 patches DoRotPt0's delta case.
  cached=enabled and re.search(r'^rot_delta2_040\s',listing,re.M) is not None
  assert rot==((bytes.fromhex('4ef9')+(sb+offset('rot_delta2_040')).to_bytes(4,'big')) if cached else hs[0]['bytes'][0x59748:0x5974e]).hex(),rot
  if cached:assert int.from_bytes(dump('rot-table.bin',sb+offset('rot_table'),4),'big')
 sfd=None
 if machine!='020':
  sfd=dump('sfd-entry.bin',b+0x6c514,6).hex()
  assert hs[0]['bytes'][0x6c514:0x6c51a].hex()=='4dfa000ad1fc'
  # Step 4: only a slave that has sfd_span_040 patches ScanFillDown's scanline loop.
  spans=enabled and re.search(r'^sfd_span_040\s',listing,re.M) is not None
  assert sfd==((bytes.fromhex('4ef9')+(sb+offset('sfd_span_040')).to_bytes(4,'big')) if spans else hs[0]['bytes'][0x6c514:0x6c51a]).hex(),sfd
 poly=None
 if machine!='020':
  poly=dump('poly-entry.bin',b+0x60d92,6).hex()
  assert hs[0]['bytes'][0x60d92:0x60d98].hex()=='244847f20400'
  # Step 5: only a slave that has poly_fill_040 patches Polygon's edge tables and fills.
  fused=enabled and re.search(r'^poly_fill_040\s',listing,re.M) is not None
  assert poly==((bytes.fromhex('4ef9')+(sb+offset('poly_fill_040')).to_bytes(4,'big')) if fused else hs[0]['bytes'][0x60d92:0x60d98]).hex(),poly
  if fused:
   for name,target in (('pf_cont',0x60d98),('pf_sp_cell',0x62a44),('pf_recip',0x62e70),('pf_colour',0x55cc8),('pf_rows',0x7cd10),('pf_cell',0x6c4c0)):
    got=int.from_bytes(dump(name+'.bin',sb+offset(name),4),'big');assert got==b+target,(name,hex(got),hex(b+target))
 sqrt=None
 if machine!='020':
  sqrt=dump('sqrt-entry.bin',b+0x4bdca,6).hex()
  assert hs[0]['bytes'][0x4bdca:0x4bdd0].hex()=='48e70f002e00'
  # Step 9: only a slave that has isqrt_040 patches @SquareRoot.
  rooted=enabled and re.search(r'^isqrt_040\s',listing,re.M) is not None
  assert sqrt==((bytes.fromhex('4ef9')+(sb+offset('isqrt_040')).to_bytes(4,'big')) if rooted else hs[0]['bytes'][0x4bdca:0x4bdd0]).hex(),sqrt
 gouraud=None
 if machine!='020':
  gouraud=dump('gouraud-entry.bin',b+0x4f840,6).hex()
  # Gouraud runs: only a 68040 slave that has gouraud_runs points @GouraudFill at it;
  # the others keep the new renderer's gouraud_fill_new (or the original bytes).
  runs=enabled and re.search(r'^gouraud_runs\s',listing,re.M) is not None
  jmp=lambda n:(bytes.fromhex('4ef9')+(sb+offset(n)).to_bytes(4,'big')).hex()
  assert gouraud==jmp('gouraud_runs') if runs else gouraud in (jmp('gouraud_fill_new'),hs[0]['bytes'][0x4f840:0x4f846].hex()),gouraud
 scan=panel=None
 if machine!='020':
  scan=dump('scan-entry.bin',b+0x6c4f2,6).hex();panel=dump('panel-entry.bin',b+0x3812,6).hex()
  # Unpatched: MOVE.L (SP)+,abs (relocated return cell $6c4c0); CLR.L -(SP)/MOVE.L D0,-(SP)/JSR (A5).
  assert hs[0]['bytes'][0x3812:0x3818].hex()=='42a72f004e95'
  # Step 3b (cockpit clipping) was rejected: only a slave that has it patches these sites.
  clip=enabled and re.search(r'^scan_fill_040\s',listing,re.M) is not None
  assert scan==((bytes.fromhex('4ef9')+(sb+offset('scan_fill_040')).to_bytes(4,'big')) if clip else bytes.fromhex('23df')+(b+0x6c4c0).to_bytes(4,'big')).hex(),scan
  assert panel==((bytes.fromhex('4eb9')+(sb+offset('panel_hook_040')).to_bytes(4,'big')) if clip else hs[0]['bytes'][0x3812:0x3818]).hex(),panel
 (out/'gate.json').write_text(json.dumps(dict(cpu=machine,original=original,enabled=enabled,shadow=ptr,hook=hook,exp=exp,custom5=v['custom5'],custom1=v['custom1'],project=project,edge=edge,mask=mask,fade=fade,rot=rot,sfd=sfd,poly=poly,sqrt=sqrt,gouraud=gouraud,scan=scan,panel=panel),indent=2))
 observer(v,end=14)(cmd,dump,bases,hs,out)
run(machine,root,Path(str(root)+'-seed'),capture,v)
