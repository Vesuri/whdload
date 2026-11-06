"""Add read-only FETOX operand capture to a separate private observer build."""
from pathlib import Path
import shutil,subprocess,difflib
root=Path(__file__).resolve().parents[1];src=root/'tmp/step9-emulator/fs-uae';dst=root/'tmp/opt20-exp-emulator/fs-uae'
assert not dst.exists();shutil.copytree(src,dst,symlinks=True)
p=dst/'src/newcpu.cpp';old=p.read_text();new=old.replace('if(off==0x50f82 ||', 'if(off==0x51682 || off==0x50f82 ||',1).replace('if(off==0x50f86 ||','if(off==0x51686 || off==0x50f86 ||',1);assert old!=new;p.write_text(new)
(root/'tmp/opt20/exp-observer.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/newcpu.cpp',tofile='b/src/newcpu.cpp')))
with (dst.parent/'build.log').open('w') as f:subprocess.run(['make','-j4'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
