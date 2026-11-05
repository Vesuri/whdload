"""Normal replay under the locally validated passive-read debugger."""
import os,hashlib,inspect
from pathlib import Path
import drive
assert hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest() in {'e0b2532ace1de7dd4d66d811488ec67ea7080b9991ee57e7190d8e31483f99cc','b4fd56d305f71183e64c2aa90663274a039044fabe8cfba5521dd25e5bd0cce3'}
drive.require_harness=lambda *args:None
import harness_a
if os.environ.get('RR_LEGACY_READS')=='1':
 src=inspect.getsource(harness_a.snapshot)
 a=src.index('    def inactive(');b=src.index('    return dict(',a)
 src=src[:a]+src[b:]
 src=src.replace("                native_ranking=ranking,rank_displayed=ranking['displayed'],\n",'')
 # replay progress needs the display rank, computed without extra memory reads.
 src=src.replace("                rank=struct", "                rank_displayed=10*(struct.unpack('>H',ranks[-2:])[0]>>4)+(struct.unpack('>H',ranks[-2:])[0]&15),\n                rank=struct")
 exec(src,harness_a.__dict__)
import road_lap_c
