#!/usr/bin/env python3
"""Capture three visible phases using an existing directed-fade calibration.

Source amiga/env.sh first. Runs startup-only Practice (CUSTOM5=2), without a
driving tape, so weather has an unobstructed flat region for the screen check.
Uses only this repository's emulator server; do not run alongside another capture.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
import _amigaxdev
from amigaxdev import barto
from weather_fade_state import locate, snapshot
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('reference',type=Path,help='Completed directed-fade capture with its frozen slave')
parser.add_argument('output',type=Path,help='New directory under ignored tmp/')
args=parser.parse_args()
reference=args.reference
root=args.output
assert root.resolve().is_relative_to(Path('tmp').resolve()), 'Output must be under tmp/'
assert not root.exists(), 'Preserve existing evidence; use a new output directory'
root.mkdir(parents=True)
config=json.loads((reference/'configuration.json').read_text())
# Existing startup-only Practice fixture leaves the sky unobstructed by the driving tape.
config['WHD_ARGS'], replacements=re.subn(r'\bCUSTOM5=\d+\b','CUSTOM5=2',config['WHD_ARGS'])
assert replacements == 1, 'Reference must identify its input fixture'
slave=reference/'slave.slave'
assert hashlib.sha256(slave.read_bytes()).hexdigest()==config['slave_sha256']
shutil.copyfile(slave,root/'slave.slave')
env=os.environ.copy()
for key in ('AMIGA_MODEL','CPU','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS'):
 env[key]=config[key]
env.update(SLAVE=str((root/'slave.slave').resolve()),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',KICKSTART=env['KICKSTART_A1200'])
assert hashlib.sha256(Path(env['KICKSTART']).read_bytes()).hexdigest()==config['kickstart_sha256']
emulator=shutil.which(env.get('FSUAE','fs-uae'))
assert emulator and hashlib.sha256(Path(emulator).read_bytes()).hexdigest()==config['emulator_sha256']
game=int((reference/'game-base.txt').read_text(),0)
base=int((reference/'dump-base.txt').read_text(),0)
env['BOOT_BREAK']=str(game+0xbc7c)
(root/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
def pd(command, path):
 result=subprocess.run([sys.executable,'tools/powerdrome.py',*command],env=env,text=True,capture_output=True,timeout=1900)
 path.write_text(result.stdout+result.stderr)
 assert result.returncode==0 and not result.stdout.startswith('ERROR'), path
 return result.stdout
server=None
try:
 result=subprocess.run([sys.executable,'tools/powerdrome.py','quit'],env=env,text=True,capture_output=True,timeout=5)
 (root/'cleanup-before.txt').write_text(result.stdout+result.stderr)
 with (root/'serve.log').open('w') as log:
  server=subprocess.Popen([sys.executable,'tools/powerdrome.py','serve'],env=env,stdout=log,stderr=subprocess.STDOUT)
 for _ in range(600):
  if 'serving on' in (root/'serve.log').read_text():break
  assert server.poll() is None, 'Server exited before anchor'
  time.sleep(1)
 else:raise AssertionError('Timed out before screenshot anchor')
 def dump(folder,prefix=''):
  for filename,lo,hi in (('chip.bin',0,int(config['CHIP_KB'])*1024),('code.bin',base,base+int(config['FAST_KB'])*1024)):
   target=folder/(prefix+filename)
   pd(['gdb',f'dump binary memory {target} {lo:#x} {hi:#x}'],folder/(prefix+filename+'.txt'))
   assert target.stat().st_size==hi-lo
 initial=root/'initial';initial.mkdir();dump(initial)
 fade=locate((initial/'chip.bin').read_bytes(),(initial/'code.bin').read_bytes(),game,base)
 assert fade is not None
 for transition in (12,7,2):
  folder=root/f'phase-{15-transition}';folder.mkdir()
  for filename in ('game-base.txt','dump-base.txt'):
   shutil.copyfile(reference/filename,folder/filename)
  (folder/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
  condition=f'*(unsigned short*){fade+16:#x} == {transition} && *(unsigned int*){fade+28:#x} == 0'
  pd(['gdb',f'break *{game+0xbc7c:#x} if {condition}\ncontinue\ndelete\ninfo registers pc'],folder/'anchor.txt')
  # Let both alternating native display buffers receive the same phase.
  for index in range(2):
   pd(['until',str(game+0xbc7c)],folder/f'settle-{index}.txt')
  dump(folder)
  before=snapshot(folder)
  assert before['published']==transition and before['negative']==0 and before['pending']==0
  pd(['profile','2',str(folder/'screen.bin')],folder/'capture.txt')
  trace=barto.load(folder/'screen.bin');assert len(trace.fields)==2
  (folder/'screen.jpg').write_bytes(trace.fields[-1].shot)
  dump(folder,'final-')
  after=snapshot(folder,True)
  assert all(before[k]==after[k] for k in ('published','positive','negative','transition','pending')), 'Screenshot crossed a fade phase'
  (folder/'phase.json').write_text(json.dumps(dict(phase=15-transition,before=before,after=after,shot_kind=trace.fields[-1].shot_kind),indent=2)+'\n')
  print(f'Captured phase {15-transition}',flush=True)
finally:
 try:pd(['quit'],root/'cleanup-after.txt')
 except Exception as error:print(f'Cleanup: {error}',file=sys.stderr)
 if server is not None:
  try:server.wait(timeout=10)
  except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=10)
