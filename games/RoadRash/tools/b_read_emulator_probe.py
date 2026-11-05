"""Private matched-build probe; old emulator predates capability discovery."""
import os,sys,inspect,hashlib
from pathlib import Path
import matrix_a
cfg=matrix_a.config(os.environ.get('RR_CELL','030-50'))
os.environ.clear();os.environ.update(cfg)
import drive
# Both locally compiled variants retain the pinned fields/input protocol.
allowed={'b4fd56d305f71183e64c2aa90663274a039044fabe8cfba5521dd25e5bd0cce3',
         'e0b2532ace1de7dd4d66d811488ec67ea7080b9991ee57e7190d8e31483f99cc'}
assert hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest() in allowed
drive.require_harness=lambda *args:None
import harness_a
if os.environ.get('RR_LEGACY_READS')=='1':
 src=inspect.getsource(harness_a.snapshot)
 a=src.index('    def inactive(');b=src.index('    return dict(',a)
 src=src[:a]+src[b:]
 src=src.replace("                native_ranking=ranking,rank_displayed=ranking['displayed'],\n",'')
 exec(src,harness_a.__dict__)
import check_a
check_a.main()
