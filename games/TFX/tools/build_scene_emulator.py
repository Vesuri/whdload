#!/usr/bin/env python3
"""Private SR fixture control, for CPU-held DMA screenshot capture only."""
from pathlib import Path
import shutil,subprocess,difflib
root=Path(__file__).resolve().parents[1];src=root/'tmp/step7-emulator/fs-uae';dst=root/'tmp/step8-emulator/fs-uae'
assert not dst.exists();shutil.copytree(src,dst,symlinks=True)
p=dst/'src/barto_gdbserver.cpp';old=p.read_text();new=old.replace('(reg<16 || reg==17)','(reg<=17)').replace('else { m68k_setpc_normal(value); fill_prefetch(); }','else if(reg==16) { regs.sr=value; MakeFromSR(); }\n                                            else { m68k_setpc_normal(value); fill_prefetch(); }')
assert new!=old;p.write_text(new)
(root/'tools/step8-scene-sr.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/barto_gdbserver.cpp',tofile='b/src/barto_gdbserver.cpp')))
with (dst.parent/'build.log').open('w') as f:subprocess.run(['make','-j4'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
