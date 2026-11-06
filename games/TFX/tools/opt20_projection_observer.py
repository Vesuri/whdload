"""Private read-only projection operand observer; no timing/model changes."""
from pathlib import Path
import shutil,subprocess,difflib
root=Path(__file__).resolve().parents[1];src=root/'tmp/opt20-exp-emulator/fs-uae';dst=root/'tmp/opt20-project-emulator/fs-uae'
assert not dst.exists();shutil.copytree(src,dst,symlinks=True)
p=dst/'src/newcpu.cpp';old=p.read_text();needle='unsigned off=tfx_pc-tfx_base;';assert old.count(needle)==1
new=old.replace(needle,needle+'\n if(off==0x55e6c && getenv("TFX_PROJECT_OPERANDS")) tfx_math.push_back({tfx_frame,off,2,m68k_dreg(regs,0),m68k_dreg(regs,1),m68k_dreg(regs,2),regs.fpcr});',1);p.write_text(new)
(root/'tmp/opt20/project-observer.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/newcpu.cpp',tofile='b/src/newcpu.cpp')))
with (dst.parent/'build.log').open('w') as f:subprocess.run(['make','-j4'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
