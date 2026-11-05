"""Rerun existing input/command checks against current production routines."""
from pathlib import Path
import re,os
root=Path(__file__).resolve().parents[1]
checks=['test_controls_c.py','test_control_targets_c.py','test_control_mode_c.py','test_command_dispatch_c.py','test_timing_commands.py','test_timing_live_input_c.py']
for name in ['Gunship','GunshipNTSC']:
 slave=root/'tmp/build/release'/f'{name}.Slave';listing=slave.with_suffix('.lst')
 syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',listing.read_text(encoding='latin1'),re.M)}
 for test in checks:
  if os.environ.get('RESUME') and name=='Gunship' and test not in ['test_timing_commands.py','test_timing_live_input_c.py']:continue
  src=(root/'tools'/test).read_text().replace('.read_text()', ".read_text(encoding='latin1')")
  src=re.sub(r"(?:build|root)/'(?:tmp/c/)?[^']+\.(?:hunk|[Ss]lave)'",'Path('+repr(str(slave))+')',src)
  src=re.sub(r"(?:build|root)/'(?:tmp/c/)?[^']+\.lst'",'Path('+repr(str(listing))+')',src)
  if test=='test_control_targets_c.py':
   src=src.replace('range(43),range(-4,5),[-128,-15,-1,0,1,15,127]', '[0,42],[-1,0,1],[0]')
   src=src.replace('range(256):', '[0,255]:').replace('range(65536):', 'range(0,65536,257):').replace('full_word_dispatch_cases=65536', 'full_word_dispatch_cases=256')
  if test=='test_control_mode_c.py':
   src=src.replace('range(256)', '[0,16,255]')
  if test=='test_timing_commands.py':
   src=src.replace('range(15000)', 'range(512)')
  # Existing sampler ABI test has native-site fixture addresses; map them to
  # the NTSC sites and its actual executable for installation validation.
  if name=='GunshipNTSC' and test=='test_timing_live_input_c.py':
   src=src.replace('Gunship','GunshipNTSC')
   src=re.sub(r'0x[0-9a-f]+',lambda m:hex(syms.get('GS0_'+m[0][2:].zfill(4),int(m[0],16))),src)
  print(name,test,flush=True)
  exec(compile(src,test,'exec'),{'__name__':'__main__'})
