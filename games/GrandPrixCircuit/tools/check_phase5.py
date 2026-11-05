#!/usr/bin/env python3
"""Check every code byte against Phase 1, allowing only exact VERIFY instruments."""
import argparse,json,os,struct,re
from pathlib import Path
from check_disabled import check
from gpc_report import regions
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();root=a.capture.resolve()
m=json.loads((root/'metadata.json').read_text());os.environ['SLAVE']=str(root/'slave.slave')
d=bytearray((root/'before.bin').read_bytes());base=m['base'];h=m['code_base'];rr={n:(lo,hi) for lo,hi,n,o in regions(d,base)}
raw=(Path(__file__).resolve().parents[1]/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit').read_bytes()
args=m['options']['WHD_ARGS'];enabled=[]
custom4=int(re.search(r'CUSTOM4=(\d+)',args).group(1)) if 'CUSTOM4=' in args else 0
sites=[(0x39e,'4ef9','4eac82fc'),(0x818c,'4eb9','6100'),(0x7094,'4eb9','0c6c'),(0x75c8,'4eb9','6100')]
for site,opcode,prefix in sites:
 off=h-base+site
 if custom4 & 2:
  assert d[off:off+6]==raw[40+site:40+site+6], hex(site)
  continue
 assert d[off:off+2]==bytes.fromhex(opcode),hex(site)
 target=struct.unpack_from('>I',d,off+2)[0]
 assert rr['slave'][0]<=target<rr['slave'][1]
 assert d[target-base:target-base+len(bytes.fromhex(prefix))]==bytes.fromhex(prefix),hex(site)
 d[off:off+6]=raw[40+site:40+site+6]
 enabled.append('display '+hex(site))
if 'CUSTOM3=1' in args:
 off=h-base+0xc12c;assert d[off:off+6]==bytes.fromhex('72004e714e71');d[off:off+6]=raw[40+0xc12c:40+0xc132];enabled.append('beam-free RNG')
for site in ([0x707a] if b'GPCVERIFY\0' in (root/'slave.slave').read_bytes() else [])+([0xc1de] if 'CUSTOM5=1' in args else []):
 off=h-base+site;assert d[off:off+2]==bytes.fromhex('4eb9');target=struct.unpack_from('>I',d,off+2)[0]
 assert rr['slave'][0]<=target<rr['slave'][1],hex(target)
 assert d[target-base:target-base+2]==bytes.fromhex('48e7')
 d[off:off+6]=raw[40+site:40+site+6];enabled.append(hex(site))
for flag,site,size,prefix in [(1,0xe06,10,'48e7'),(4,0x729a,8,'48e7')]:
 if not ((custom4 & 1) if flag==4 else f'CUSTOM{flag}=1' in args):continue
 off=h-base+site;assert d[off:off+2]==bytes.fromhex('4eb9')
 target=struct.unpack_from('>I',d,off+2)[0]
 assert rr['slave'][0]<=target<rr['slave'][1]
 assert d[off+6:off+size]==bytes.fromhex('4e71')*((size-6)//2)
 assert d[target-base:target-base+2]==bytes.fromhex(prefix)
 d[off:off+size]=raw[40+site:40+site+size];enabled.append(hex(site))
check(d,base,m['options']['CPU'])
print('Exact VERIFY patch sites:',', '.join(enabled))
# A corruption outside these sites must still be rejected.
d[h-base+0x39e]^=1
try:check(d,base,m['options']['CPU'])
except AssertionError:print('Negative control: corrupted swap instruction rejected')
else:raise AssertionError('negative control accepted')
