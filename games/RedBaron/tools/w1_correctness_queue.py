"""Run after the primary queue; all emulation is sequential."""
import subprocess,sys
for machine in ('a500','020','030'):
 for scene in ('bank','dense'):
  subprocess.run([sys.executable,'tools/w1_scene_twins.py','--machine',machine,'--scene',scene],check=True)
 print('CORRECTNESS COMPLETE',machine,flush=True)
