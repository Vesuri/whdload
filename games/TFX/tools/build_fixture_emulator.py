#!/usr/bin/env python3
"""Build private fixture backend from the configured step 5 observer tree."""
from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1]
src=root/'tmp/step5-emulator/fs-uae';dst=root/'tmp/step7-emulator/fs-uae'
assert not dst.exists();shutil.copytree(src,dst,symlinks=True)
with (root/'tools/step7-fixture.patch').open() as f:subprocess.run(['patch','-p1'],cwd=dst,stdin=f,check=True)
with (dst.parent/'build.log').open('w') as f:subprocess.run(['make','-j4'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
