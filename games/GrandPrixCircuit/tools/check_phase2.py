#!/usr/bin/env python3
"""Check every code byte against Phase 1, allowing only exact VERIFY instruments."""
import argparse,json,os,struct
from pathlib import Path
from check_disabled import check
from gpc_report import regions
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();root=a.capture.resolve()
m=json.loads((root/'metadata.json').read_text());os.environ['SLAVE']=str(root/'slave.slave')
d=bytearray((root/'before.bin').read_bytes());base=m['base'];h=m['code_base'];rr={n:(lo,hi) for lo,hi,n,o in regions(d,base)}
raw=(Path(__file__).resolve().parents[1]/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit').read_bytes()
args=m['options']['WHD_ARGS'];enabled=[]
if 'CUSTOM3=1' in args:
 off=h-base+0xc12c;assert d[off:off+6]==bytes.fromhex('72004e714e71');d[off:off+6]=raw[40+0xc12c:40+0xc132];enabled.append('beam-free RNG')
for site in [0x707a]+([0xc1de] if 'CUSTOM5=1' in args else []):
 off=h-base+site;assert d[off:off+2]==bytes.fromhex('4eb9');target=struct.unpack_from('>I',d,off+2)[0]
 assert rr['slave'][0]<=target<rr['slave'][1],hex(target)
 assert d[target-base:target-base+2]==bytes.fromhex('48e7')
 d[off:off+6]=raw[40+site:40+site+6];enabled.append(hex(site))
check(d,base,m['options']['CPU'])
print('Exact VERIFY patch sites:',', '.join(enabled))
# A corruption outside these sites must still be rejected.
d[h-base+0x39e]^=1
try:check(d,base,m['options']['CPU'])
except AssertionError:print('Negative control: corrupted swap instruction rejected')
else:raise AssertionError('negative control accepted')
