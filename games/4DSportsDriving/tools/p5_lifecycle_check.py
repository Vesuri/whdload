import subprocess,sys
subprocess.run([sys.executable,'tools/p5_crash_finish.py',sys.argv[1]],check=True)
