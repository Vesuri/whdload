"""Local copy: apply the same profiler range/length fixes without per-boot LLDB.
No CPU emulation, memory timing, DMA, guest code or machine setup is changed.
"""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from capture_demo import ROOT,sha
src=Path(shutil.which('fs-uae'));b=bytearray(src.read_bytes());assert sha(src)=='ffd5c960322f445e72a02bc47c84312dfb8b189ce8327b55e1211d7fa170148d'
patches=[(0x5f380,'8b3d7ef627038b357cf62703','31ff90909090beffffff7f90'),(0x5bfb9,'b964000000','89c1909090')]
for addr,old,new in patches:
 off=addr-0x4000;assert b[off:off+len(bytes.fromhex(old))]==bytes.fromhex(old);assert len(old)==len(new);b[off:off+len(bytes.fromhex(old))]=bytes.fromhex(new)
out=ROOT/'tmp/profile-emulator';out.mkdir(exist_ok=False)
for name in ['lib','data','fs-uae.dat']:(out/name).symlink_to(src.parent/name,target_is_directory=(src.parent/name).is_dir())
p=out/'fs-uae';p.write_bytes(b);p.chmod(0o755);subprocess.run(['codesign','--force','--sign','-',str(p)],check=True)
(out/'patches.json').write_text(json.dumps(dict(original_sha256=sha(src),patched_sha256=sha(p),patches=patches),indent=2)+'\n');print(p)
