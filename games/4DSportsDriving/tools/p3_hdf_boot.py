"""Create disposable native IDE images, avoiding UAE directory-filesystem cache restrictions."""
from pathlib import Path
import subprocess,sys
run=Path(sys.argv[1]).resolve()
for n in (0,1):
 image=run/f'dh{n}.hdf';image.unlink(missing_ok=True)
 subprocess.run(['xdftool',str(image),'create','chs=1024,1,32','+','format',f'DH{n}','DOS1','+','write',str(run/f'dh{n}'),'','add'],check=True)
