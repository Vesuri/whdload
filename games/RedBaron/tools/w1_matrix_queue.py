"""Run remaining controlled W1 cases serially; stop on the first failure."""
import subprocess,sys
for machine,mask in [('a500',1),('a500',3),('020',0),('020',1),('020',3),('030',0),('030',1),('030',3)]:
 print('START',machine,mask,flush=True)
 subprocess.run([sys.executable,'tools/w1_controlled.py','--machine',machine,'--mask',str(mask)],check=True)
 if machine!='030':subprocess.run([sys.executable,'tools/w1_cost_report.py',f'tmp/prof/w1-controlled-{machine}-{mask}','--mask',str(mask)],check=True)
 print('DONE',machine,mask,flush=True)
