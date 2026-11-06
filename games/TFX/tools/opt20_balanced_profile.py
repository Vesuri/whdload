"""Same-address, same-length pre-window patch on BOTH sides of an A/B pair."""
import os,sys,json,re
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
from map_symbols import load
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],custom4=18,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true '+os.environ.get('EXTRA_UAE',''),expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
# CUSTOM arguments are baked into the seed's dh0.hdf at enrolment: a TEST_SEED run
# boots with the control's arguments. Select slave variants with PROJECT_SYMBOL instead.
def capture(cmd,dump,bases,hs,out):
 kind=os.environ['PATCH_KIND'];control=bool(os.environ.get('CONTROL'));mask=None
 if kind=='copy':
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+0x19fe,4),'big')-sym('do_swap_screen');length=int(os.environ.get('COPY_LEN','90'));address=sb+sym('delta_shadow')-length
  # COPY_DONOR (slave path without extension, default flat-edge-verified): the build
  # whose 90-byte compare loop the control runs. The loop is position-independent.
  stem=os.environ.get('COPY_DONOR',str(ROOT/'tmp/opt20/flat-edge-verified'))
  donor=Path(stem+'.lst').read_text(encoding='latin1');end=int(re.search(r'^delta_shadow\s+00:([0-9A-Fa-f]+)',donor,re.M)[1],16)
  # A larger slot (COPY_LEN) holds the donor's 90-byte loop zero-padded: same address and length.
  original=load(Path(stem+'.slave'))[0]['data'][end-90:end].ljust(length,b'\0')
 elif kind=='gouraud':
  # Same address/length: JMP gouraud_fill_new (control) or JMP gouraud_runs (candidate).
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+0x19fe,4),'big')-sym('do_swap_screen')
  address=bases[0]+0x4f840;original=bytes.fromhex('4ef9')+(sb+sym('gouraud_fill_new')).to_bytes(4,'big');mask=(0x4f840,0x4f846)
 else:
  start,size={'edge':(0x6c534,12),'project':(0x55e32,6),'exp':(0x51682,4),'mask':(0x4e400,6),'scan':(0x6c4f2,6),'fade':(0x249a,6),'rot':(0x59748,6),'sfd':(0x6c514,6),'poly':(0x60d92,6),'sqrt':(0x4bdca,6)}[kind];address=bases[0]+start;original=hs[0]['bytes'][start:start+size];mask=(start,start+size)
  if kind=='mask':
   # MOVEQ #7,D0 / MOVE.L A1,$4e52a: the hunk image holds the unrelocated absolute.
   assert original.hex()=='700723c90004'
   import struct;original=bytes.fromhex('700723c9')+struct.pack('>I',bases[0]+0x4e52a)[:2]
  if kind=='rot':assert original.hex()=='4c9800032604'  # MOVEM.W (A0)+,D0-D1 / MOVE.L D4,D3
  if kind=='sfd':assert original.hex()=='4dfa000ad1fc'  # LEA (PC),A6 / ADDA.L #55960: no relocation
  if kind=='poly':assert original.hex()=='244847f20400'  # MOVEA.L A0,A2 / LEA (A2,D0.W*4),A3: no relocation
  if kind=='sqrt':assert original.hex()=='48e70f002e00'  # MOVEM.L D4-D7,-(SP) / MOVE.L D0,D7: no relocation
  if kind=='fade':assert original.hex()=='594f48e73f34'  # SUBQ.W #4,SP / MOVEM.L: no relocation
  if kind=='scan':
   # MOVE.L (SP)+,abs: the absolute is the return cell at $6c4c0 (unrelocated in the image).
   assert original[:2].hex()=='23df'
   import struct;original=bytes.fromhex('23df')+struct.pack('>I',bases[0]+0x6c4c0)
 candidate=dump('candidate-patch.bin',address,len(original));patch=original if control else candidate
 if kind=='project' and os.environ.get('PROJECT_SYMBOL') and not control:
  # Same address/length: JMP to another routine of the same slave (DELTA_LISTING).
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+0x19fe,4),'big')-sym('do_swap_screen')
  assert candidate==bytes.fromhex('4ef9')+(sb+sym('project_fpu_040')).to_bytes(4,'big'),candidate.hex()
  patch=bytes.fromhex('4ef9')+(sb+sym(os.environ['PROJECT_SYMBOL'])).to_bytes(4,'big')
 # CLOCK_NORMALIZE=1: the boot takes 1-4 vblanks more or less run to run, and the
 # vblank clock (_vblank_clock $4d884) and its four copies are the only entry-state
 # differences. Both sides write the same fixed values (a clip-off-r control boot) with
 # the same calls in the same order, so MATCH_ENTRY stays exact and the pair balanced.
 clocks=[(0,0x4d85a,0x614),(0,0x4d884,0x614),(1,0x10678,0x60f),(1,0x13de0,0x60f),(1,0x17012,0x4a9)] if os.environ.get('CLOCK_NORMALIZE') else []
 for hunk,offset,value in clocks:
  cmd(f'monitor tfxmem {bases[hunk]+offset:x} {value:08x}');assert dump('clock.bin',bases[hunk]+offset,4)==value.to_bytes(4,'big')
 # tfxmem writes back/invalidate caches. Do the same calls (one per chunk), same address/length,
 # for either mode, including a redundant write of the enabled instructions.
 # Monitor writes over ~90 bytes time out: split longer patches into equal chunks
 # (same calls on both sides).
 chunks=-(-len(patch)//90);step=-(-len(patch)//chunks)
 for o in range(0,len(patch),step):cmd(f'monitor tfxmem {address+o:x} {patch[o:o+step].hex()}')
 assert dump('selected-patch.bin',address,len(patch))==patch
 (out/'balanced-setup.json').write_text(json.dumps(dict(kind=kind,control=control,address=address,length=len(patch),tfxmem_calls=chunks+len(clocks),clocks=[[h,o,v] for h,o,v in clocks],original=original.hex(),candidate=candidate.hex(),selected=patch.hex()),indent=2))
 registers=cmd('info registers');(out/'setup-registers.txt').write_text(registers)
 if os.environ.get('MATCH_ENTRY'):
  ref=Path(os.environ['MATCH_ENTRY']);equal=[]
  for i,(address,hunk) in enumerate(zip(bases,hs)):
   actual=bytearray(dump(f'matching-entry-hunk{i}.bin',address,hunk['size']));expected=bytearray((ref/f'entry-hunk{i}.bin').read_bytes())
   if i==0 and mask:actual[mask[0]:mask[1]]=expected[mask[0]:mask[1]]
   equal.append(actual==expected)
  equal.append(registers==(ref/'setup-registers.txt').read_text())
  (out/'entry-match.json').write_text(json.dumps(equal));assert all(equal),('startup mismatch',equal)
 def observed_dump(name,address,size):
  if name=='start-hunk0.bin':cmd(f'monitor tfxstart {bases[0]}')
  if name=='end-hunk0.bin':cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,address,size)
 observer(v,end=int(os.environ.get('END_FIELD','2002')))(cmd,observed_dump,bases,hs,out)
 dump('chip.bin',0,0x200000);dump('fast.bin',0x40000000,0x2000000)
run('040',out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
