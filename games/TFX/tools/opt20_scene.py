#!/usr/bin/env python3
"""Controlled game-time visual test; not a performance measurement."""
import os,sys,json,re,struct
from pathlib import Path
from replay_flight import ROOT,run
from baseline_matrix import VARIANTS
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();machine=sys.argv[2] if len(sys.argv)>2 else '040';os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--uae_fpu_no_unimplemented=true'+(' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true' if os.environ.get('SCENE_NOMMU') else ''))
# Stop at the FIRST timestep computation, before the first simulation update.
v['swap']=0x1ac36
v['custom4']=int(os.environ.get('CUSTOM4','18'))
v['custom5']=int(os.environ.get('CUSTOM5','0'));v['custom1']=int(os.environ.get('CUSTOM1','0'))
def observe(cmd,dump,bases,hs,out):
 base=bases[0]
 listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
 def offset(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 sb=int.from_bytes(dump('swap-target.bin',base+0x19fe,4),'big')-offset('do_swap_screen')
 if os.environ.get('COPY_BENCH'):
  from map_symbols import load
  length=int(os.environ.get('COPY_LEN','90'))
  target=sb+offset('delta_shadow')-length
  current=dump('copy-loop.bin',target,length)
  stem=os.environ.get('COPY_DONOR',str(ROOT/'tmp/opt20/flat-edge-verified'))
  donor=Path(stem+'.lst').read_text(encoding='latin1')
  end=int(re.search(r'^delta_shadow\s+00:([0-9A-Fa-f]+)',donor,re.M)[1],16)
  original=load(Path(stem+'.slave'))[0]['data'][end-90:end].ljust(length,b'\0')
  selected=original if os.environ.get('WORD_COPY_OFF') else current
  for o in range(0,length,75):cmd(f'monitor tfxmem {target+o:x} {selected[o:o+75].hex()}')
  assert dump('copy-selected.bin',target,length)==selected
 if os.environ.get('DELTA_OFF'):
  branch=int(re.search(r'^00:([0-9A-Fa-f]+) [0-9A-F]+.*beq.b\s+\.fullcopy',listing,re.M)[1],16)
  raw=dump('delta-branch.bin',sb+branch,2);assert raw[0]==0x67
  cmd(f'monitor tfxmem {sb+branch:x} 60');assert dump('delta-off.bin',sb+branch,2)==bytes([0x60,raw[1]])
 if os.environ.get('FLAT_EDGE_OFF'):
  raw=hs[0]['bytes'][0x6c534:0x6c540]
  assert dump('edge-live.bin',base+0x6c534,12).hex()=='e9c136c578209843e9c256c5'
  cmd(f'monitor tfxmem {base+0x6c534:x} {raw.hex()}')
  assert dump('edge-disabled.bin',base+0x6c534,12)==raw
 if os.environ.get('PROJECT_OFF'):
  assert dump('project-live.bin',base+0x55e32,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x55e32:0x55e38]
  cmd(f'monitor tfxmem {base+0x55e32:x} {raw.hex()}')
  assert dump('project-disabled.bin',base+0x55e32,6)==raw
 if os.environ.get('MASK_OFF'):
  # Restore MOVEQ #7,D0 / MOVE.L A1,abs: only the high word of the absolute was patched.
  assert dump('mask-live.bin',base+0x4e400,2)==bytes.fromhex('4ef9')
  raw=bytes.fromhex('700723c9')+struct.pack('>I',base+0x4e52a)[:2]
  cmd(f'monitor tfxmem {base+0x4e400:x} {raw.hex()}')
  assert dump('mask-disabled.bin',base+0x4e400,8)==raw+struct.pack('>I',base+0x4e52a)[2:]
 if os.environ.get('ROT_OFF'):
  assert dump('rot-live.bin',base+0x59748,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x59748:0x5974e];assert raw.hex()=='4c9800032604'
  cmd(f'monitor tfxmem {base+0x59748:x} {raw.hex()}')
  assert dump('rot-disabled.bin',base+0x59748,6)==raw
 if os.environ.get('POLY_OFF'):
  assert dump('poly-live.bin',base+0x60d92,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x60d92:0x60d98];assert raw.hex()=='244847f20400'
  cmd(f'monitor tfxmem {base+0x60d92:x} {raw.hex()}')
  assert dump('poly-disabled.bin',base+0x60d92,6)==raw
 if os.environ.get('SQRT_OFF'):
  assert dump('sqrt-live.bin',base+0x4bdca,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x4bdca:0x4bdd0];assert raw.hex()=='48e70f002e00'
  cmd(f'monitor tfxmem {base+0x4bdca:x} {raw.hex()}')
  assert dump('sqrt-disabled.bin',base+0x4bdca,6)==raw
 if os.environ.get('GOURAUD_OFF'):
  # Back to the new renderer's chunky fill and c2p (what 020/030/060 run).
  live=dump('gouraud-live.bin',base+0x4f840,6);assert live==bytes.fromhex('4ef9')+(sb+offset('gouraud_runs')).to_bytes(4,'big'),live.hex()
  raw=bytes.fromhex('4ef9')+(sb+offset('gouraud_fill_new')).to_bytes(4,'big')
  cmd(f'monitor tfxmem {base+0x4f840:x} {raw.hex()}')
  assert dump('gouraud-disabled.bin',base+0x4f840,6)==raw
 if os.environ.get('SFD_OFF'):
  assert dump('sfd-live.bin',base+0x6c514,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x6c514:0x6c51a];assert raw.hex()=='4dfa000ad1fc'
  cmd(f'monitor tfxmem {base+0x6c514:x} {raw.hex()}')
  assert dump('sfd-disabled.bin',base+0x6c514,6)==raw
 if os.environ.get('FADE_OFF'):
  assert dump('fade-live.bin',base+0x249a,2)==bytes.fromhex('4ef9')
  raw=hs[0]['bytes'][0x249a:0x24a0];assert raw.hex()=='594f48e73f34'
  cmd(f'monitor tfxmem {base+0x249a:x} {raw.hex()}')
  assert dump('fade-disabled.bin',base+0x249a,6)==raw
 if os.environ.get('SCAN_OFF'):
  # Restore MOVE.L (SP)+,abs with the relocated address of the return cell at $6c4c0.
  assert dump('scan-live.bin',base+0x6c4f2,2)==bytes.fromhex('4ef9')
  raw=bytes.fromhex('23df')+struct.pack('>I',base+0x6c4c0)
  assert hs[0]['bytes'][0x6c4f2:0x6c4f4]==raw[:2]
  cmd(f'monitor tfxmem {base+0x6c4f2:x} {raw.hex()}')
  assert dump('scan-disabled.bin',base+0x6c4f2,6)==raw
 if os.environ.get('EXP_OFF'):
  assert dump('exp-live.bin',base+0x51682,4)==bytes.fromhex('4eb80220')
  cmd(f'monitor tfxmem {base+0x51682:x} f2001c10')
  assert dump('exp-disabled.bin',base+0x51682,4)==bytes.fromhex('f2001c10')
 coherence=[]
 def scalar(name):
  cmd(f'monitor tfxsync {sb+offset(name):x} 4')
  return int.from_bytes(dump(name+'.bin',sb+offset(name),4),'big')
 fast=scalar('fast_buf');shadow=scalar('delta_shadow');logptr=scalar('_logbase_ptr')
 for name in os.environ.get('RESTORE_RENDER','').split(','):
  if not name:continue
  sites={'line':[0x4de00],'strip':[0x500dc],'box':[0x4dba0,0x4dbc8]}[name]
  for o in sites:
   raw=hs[0]['bytes'][o:o+6];cmd(f'monitor tfxmem {base+o:x} {raw.hex()}');assert dump(f'restored-{o:x}.bin',base+o,6)==raw
 swaps=0;pending_publication=False;tape=json.loads((ROOT/'tools/flight.tape.json').read_text())
 original=hs[0]['bytes'][0x1ac36:0x1ac46]
 assert dump('timestep-original.bin',base+0x1ac36,16)==original
 # MOVEQ #5,D0; MOVE.W D0,-2980(A4); five NOPs. D1 is overwritten before use.
 replacement=bytes.fromhex('70053940f45c'+'4e71'*5)
 cmd(f'monitor tfxmem {base+0x1ac36:x} {replacement.hex()}')
 assert dump('timestep-fixture.bin',base+0x1ac36,16)==replacement
 joy=base+0x40f7e
 assert dump('joystick-original.bin',joy,6)==hs[0]['bytes'][0x40f7e:0x40f84]
 def joystick(value):
  payload=bytes.fromhex('323c00004e71')
  cmd(f'monitor tfxmem {joy:x} {payload.hex()}')
  # Deliver the resolved right-arrow latch synchronously, as ReadDJoy does.
  latch=dump('joystick-latch.bin',base+0x40f60,2)
  cmd(f'monitor tfxmem {base+0x40f60:x} {bytes(x&~8 for x in latch).hex()}')
  cmd(f'monitor tfxmem {base+0x40ce5:x} {"ff" if value else "00"}')
 joystick(0)
 if os.environ.get('EXP_AUDIT'):cmd(f'monitor tfxstart {base}')
 cmd('delete breakpoints');cmd(f'break *{base+0x19fc:#x}');cmd(f'break *{base+0x4c474:#x}');publications=[]
 while True:
  reply=cmd('continue');cmd('maintenance flush register-cache')
  pc=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)
  if pc==base+0x19fc:
   swaps+=1;pending_publication=True
   if os.environ.get('VIEW_TAPE'):
    viewkeys={5:(0x51,1),9:(0x51,0),15:(0x52,1),19:(0x52,0),25:(0x54,1),29:(0x54,0),35:(0x55,1),39:(0x55,0),45:(0x50,1),49:(0x50,0)}
    if swaps in viewkeys:
     key,value=viewkeys[swaps];cmd(f'monitor key {key:x} {value}')
   if os.environ.get('FOLLOW_TAPE'):
    # Follow camera (F5) from swap 25 to the end, as tools/follow.tape.json.
    if swaps in (25,29):cmd(f'monitor key 54 {int(swaps==25)}')
   target=scalar('old_bufs');cmd(f'monitor tfxsync {logptr:x} 2');page=int.from_bytes(dump('log-index.bin',logptr,2),'big');assert page in (0,4)
   if shadow and not os.environ.get('DELTA_OFF'):
    cmd(f'monitor tfxsync {sb+offset("delta_seen"):x} 8')
    initialized=dump('shadow-seen.bin',sb+offset('delta_seen')+page,1)[0]
    if initialized:
     addr=shadow+(page//4)*64000;cmd(f'monitor tfxsync {addr:x} 64000')
     cached=dump('shadow-before.bin',addr,64000);actual=dump('chip-before.bin',target,64000)
     coherence.append(dict(swap=swaps,before_equal=cached==actual));assert cached==actual,('external chip writer',swaps)
   for e in tape['flight_inputs']:
    if e['swap']==swaps:
     assert e['event']=='JOY2_RIGHT';joystick(e['value'])
   continue
  assert pc==base+0x4c474
  assert pending_publication,('SetPage outside the counted flight swap',swaps)
  pending_publication=False
  target=scalar('old_bufs');cmd(f'monitor tfxsync {fast:x} 64000')
  expected=dump('fast-after.bin',fast,64000);actual=dump('chip-after.bin',target,64000)
  coherence.append(dict(swap=swaps,after_equal=actual==expected));assert actual==expected,('incomplete copy',swaps)
  copper=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a0'))[1],16);publications.append(dict(swap=swaps,copper=copper))
  if swaps in [1,10,30,45,57,200,400,600]:
   def register(name):
    cmd('maintenance flush register-cache');return int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $'+name))[1],16)
   original_sr=register('sr');cmd(f'monitor tfxreg 16 {original_sr|0x700:x}')
   cmd('stepi');resume_pc=register('pc');assert resume_pc==base+0x4c47a
   resume_sr=(register('sr')&~0x700)|(original_sr&0x700)
   saved={n:register(n) for n in ['d'+str(i) for i in range(8)]+['a'+str(i) for i in range(7)]+['sp']}
   # Hold the CPU in the fixture's last NOP slot; DMA keeps displaying this frame.
   hold=base+0x1ac44;cmd(f'monitor tfxmem {hold:x} 60fe');cmd(f'monitor tfxreg 17 {hold:x}')
   p=out/f'swap-{swaps:03d}.trace';cmd(f'monitor profile 2 "" "{p}"');t=barto.load(p);f=t.fields[-1]
   assert register('pc')==hold and all(register(n)==value for n,value in saved.items())
   cmd(f'monitor tfxmem {hold:x} 4e71');cmd(f'monitor tfxreg 17 {resume_pc:x}');cmd(f'monitor tfxreg 16 {resume_sr:x}')
   # The last full field must fetch all eight planes selected by this publication.
   words=dict(struct.unpack_from('>HH',t.chip,o) for o in range(copper,copper+192,4))
   planes=[(words[0xe0+4*i]<<16)|words[0xe2+4*i] for i in range(8)]
   first={}
   for o in range(0,len(f.dma),f.dma_size):
    if struct.unpack_from('<h',f.dma,o+29)[0]==6:first.setdefault(struct.unpack_from('<H',f.dma,o)[0],struct.unpack_from('<I',f.dma,o+12)[0])
   assert [first[0x110+2*i] for i in range(8)]==planes
   (out/f'swap-{swaps:03d}.png').write_bytes(f.shot)
   print(out.name,'published scene',swaps,flush=True)
  if swaps==int(os.environ.get('SCENE_SWAPS','57')):break
 for i,(a,h) in enumerate(zip(bases,hs)):
  cmd(f'monitor tfxsync {a:x} {h["size"]}');dump(f'end-hunk{i}.bin',a,h['size'])
 assert [p['swap'] for p in publications]==list(range(1,swaps+1))
 if os.environ.get('EXP_AUDIT'):cmd(f'monitor tfxsave {out}/profile.csv')
 if re.search(r'^clip_miss\s',listing,re.M):
  stats={n:scalar(n) for n in ['clip_ok','clip_miss','panel_scratch']}
  (out/'clip-stats.json').write_text(json.dumps(stats,indent=2));print('clip',stats,flush=True)
 (out/'coherence.json').write_text(json.dumps(coherence,indent=2))
 (out/'publications.json').write_text(json.dumps(publications,indent=2))
 (out/'controlled-time.json').write_text(json.dumps(dict(fixture='fixed timestep clamp',offset=0x1ac36,original=original.hex(),replacement=replacement.hex(),delta=5,swaps=swaps,input_fixture='native resolved right-arrow latch; neutral hardware input',input_tape=tape['flight_inputs']),indent=2))

run(machine,out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),observe,v)
