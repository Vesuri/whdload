import subprocess,sys
for tag in ['control','background']:
 subprocess.run([sys.executable,'tools/run_checks_e.py',f'tmp/e-{tag}-fixed-check',f'tmp/e-{tag}-fixed-build/RoadRash-verify.slave','040-25','060-50'],check=True)
