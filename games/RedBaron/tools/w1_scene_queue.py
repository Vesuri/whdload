"""Run only after the primary queue exits. Every emulator operation is sequential."""
import subprocess,sys
for machine in ('a500','020','030'):
 for scene in ('bank','dense'):
  for mask in (0,1,3):
   subprocess.run([sys.executable,'tools/w1_scene_capture.py','--machine',machine,'--scene',scene,'--mask',str(mask)],check=True)
   if machine!='030':subprocess.run([sys.executable,'tools/w1_window_cost_report.py',f'tmp/prof/w1-scene-{machine}-{scene}-{mask}','--mask',str(mask)],check=True)
 print('SCENES COMPLETE',machine,flush=True)
