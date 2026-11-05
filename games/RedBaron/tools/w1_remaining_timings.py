"""Single sequential queue; stop on any failure."""
import subprocess,sys
subprocess.run([sys.executable,'tools/w1_030_clock_queue.py'],check=True)
for machine in ('a500','020'):
 for mask in (0,1,3):
  subprocess.run([sys.executable,'tools/w1_hot_capture.py','--machine',machine,'--mask',str(mask)],check=True)
  subprocess.run([sys.executable,'tools/w1_window_cost_report.py',f'tmp/prof/w1-hot-{machine}-{mask}','--mask',str(mask)],check=True)
subprocess.run([sys.executable,'tools/w1_scene_queue.py'],check=True)
