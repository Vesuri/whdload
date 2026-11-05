from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
for group in ['exact','tracecontrol','trace']:
 print('RUN',group,flush=True)
 subprocess.run([sys.executable,str(r/'tools/run_h13_checks.py'),group],check=True)
 if group.startswith('trace'):
  arm='control' if group=='tracecontrol' else 'candidate';subprocess.run([sys.executable,str(r/'tools/analyze_h13_trace.py'),str(r/f'tmp/step5/hi25-profile-040-40-bce-h13-grid-{arm}')],check=True)
 print('PASS',group,flush=True)
subprocess.run([sys.executable,str(r/'tools/run_h13_safety.py')],check=True)
