#!/usr/bin/env python3
"""Check actual replay I/O acceptance markers and saved files."""
import argparse,json,struct,hashlib,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--saved-dir',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(Path(__file__).with_name('replay_file_check.py')),str(a.capture)],check=True)
b=(a.capture/'memory.bin').read_bytes();i=b.index(b'4DRPLIO!');v,n,passed=struct.unpack_from('>HHI',b,i+8);assert (v,n,passed)==(1,12,12),(v,n,passed)
assert b[i+16:i+20]==b'IO01'
assert b[i+20+61630:i+24+61630]==b'IO02'
assert b[i+24+2*61630:i+28+2*61630]==b'IO03'
tagged=(a.saved_dir/'A4000-io-test.rpl').read_bytes();assert tagged==(a.capture/'golden.r50').read_bytes()
root=Path(__file__).resolve().parents[1];original=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/DEFAULT.rpl').read_bytes()
native=(a.saved_dir/'A2500-io-test.rpl').read_bytes();assert native==original
for name in ('A4000-io-test.rpl','A2500-io-test.rpl'):(a.capture/name).write_bytes((a.saved_dir/name).read_bytes())
r=dict(checks=passed,guards=True,tagged_bytes=len(tagged),native_bytes=len(native),native_original_identical=True,tagged_packet_identical=True,tagged_sha256=hashlib.sha256(tagged).hexdigest())
(a.capture/'replay-io-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
