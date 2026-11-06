"""Strict profiling with optional pre-window restore of selected original fill entries."""
import os,sys,struct,shutil,re,json
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],custom4=int(os.environ.get('CUSTOM4','18')),extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true',expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
def capture(cmd,dump,bases,hs,out):
 if os.environ.get('DELTA_OFF'):
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  swap=int(re.search(r'^do_swap_screen\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  branch=int(re.search(r'^00:([0-9A-Fa-f]+) [0-9A-F]+.*beq.b\s+\.fullcopy',listing,re.M)[1],16)
  sb=struct.unpack('>I',dump('swap-target.bin',bases[0]+0x19fe,4))[0]-swap
  before=dump('delta-branch.bin',sb+branch,2);assert before[0]==0x67
  cmd(f'monitor tfxmem {sb+branch:x} 60');assert dump('delta-branch-off.bin',sb+branch,2)==bytes([0x60,before[1]])
 for name in os.environ.get('RESTORE_FILLS','').split(','):
  if not name:continue
  offset={'normal':0x6c4f2,'gouraud':0x4f840,'texture':0x4f9f8}[name];data=hs[0]['bytes'][offset:offset+6]
  if name=='normal':data=data[:2]+struct.pack('>I',bases[0]+0x6c4c0)
  cmd(f'monitor tfxmem {bases[0]+offset:x} {data.hex()}');assert dump(name+'-restored.bin',bases[0]+offset,6)==data
 if os.environ.get('WORD_COPY_OFF'):
  from map_symbols import load
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda name:int(re.search(r'^'+name+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('copy-swap-target.bin',bases[0]+0x19fe,4),'big')-sym('do_swap_screen')
  donor=(ROOT/'tmp/opt20/flat-edge-verified.lst').read_text(encoding='latin1')
  end=int(re.search(r'^delta_shadow\s+00:([0-9A-Fa-f]+)',donor,re.M)[1],16)
  raw=load(ROOT/'tmp/opt20/flat-edge-verified.slave')[0]['data'][end-90:end]
  assert len(raw)==90 and raw[:4].hex()=='303c0f9f'
  target=sb+sym('delta_shadow')-90
  cmd(f'monitor tfxmem {target:x} {raw.hex()}')
  assert dump('original-copy-loop.bin',target,90)==raw
 if os.environ.get('FLAT_EDGE_OFF'):
  raw=hs[0]['bytes'][0x6c534:0x6c540]
  assert dump('edge-live.bin',bases[0]+0x6c534,12).hex()=='e9c136c578209843e9c256c5'
  cmd(f'monitor tfxmem {bases[0]+0x6c534:x} {raw.hex()}')
  assert dump('edge-disabled.bin',bases[0]+0x6c534,12)==raw
 if os.environ.get('PROJECT_OFF'):
  assert dump('project-live.bin',bases[0]+0x55e32,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x55e32:0x55e38]
  cmd(f'monitor tfxmem {bases[0]+0x55e32:x} {raw.hex()}')
  assert dump('project-disabled.bin',bases[0]+0x55e32,6)==raw
 if os.environ.get('FLAT_OFF'):
  assert dump('flat-live.bin',bases[0]+0x6c5d4,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x6c5d4:0x6c5da]
  assert raw.hex()=='d2419d86efd1'
  cmd(f'monitor tfxmem {bases[0]+0x6c5d4:x} {raw.hex()}')
  assert dump('flat-disabled.bin',bases[0]+0x6c5d4,6)==raw
 if os.environ.get('EXP_OFF'):
  assert dump('exp-live.bin',bases[0]+0x51682,4)==bytes.fromhex('4eb80220')
  cmd(f'monitor tfxmem {bases[0]+0x51682:x} f2001c10')
  assert dump('exp-disabled.bin',bases[0]+0x51682,4)==bytes.fromhex('f2001c10')
 if os.environ.get('MATCH_ENTRY'):
  reference=Path(os.environ['MATCH_ENTRY'])
  matches=[]
  for i,(address,hunk) in enumerate(zip(bases,hs)):
   actual=bytearray(dump(f'matching-entry-hunk{i}.bin',address,hunk['size']))
   expected=bytearray((reference/f'entry-hunk{i}.bin').read_bytes())
   if i==0 and not os.environ.get('MATCH_ALL'):
    start,end=(0x6c534,0x6c540) if os.environ.get('MATCH_EDGE') else (0x55e32,0x55e38)
    actual[start:end]=expected[start:end]
   matches.append(actual==expected)
  (out/'entry-match.json').write_text(json.dumps(matches))
  assert all(matches),('startup state mismatch',matches)
 def observed_dump(name,addr,size):
  if name=='start-hunk0.bin':cmd(f'monitor tfxstart {bases[0]}')
  if name=='end-hunk0.bin':cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,addr,size)
 observer(v,end=int(os.environ.get('END_FIELD','252')))(cmd,observed_dump,bases,hs,out)
 dump('chip.bin',0,0x200000);dump('fast.bin',0x40000000,0x2000000)
run('040',out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
shutil.copy(__file__,out/Path(__file__).name)
