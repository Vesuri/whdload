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
for site in ([0x707a] if b'GPCVERIFY\0' in (root/'slave.slave').read_bytes() else [])+([0xc1de] if re.search(r'CUSTOM5=([1-9][0-9]*)',args) else []):
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
# Read current hook declarations, require the exact assembled target, and check
# every unmodified tail byte for whole-function jumps before restoring originals.
source=Path(__file__).resolve().parents[1]/'src'
listing=(root/'slave.slave.lst').read_text(encoding='latin1')
def symbol(name):
 match=re.search(r'^'+name+r'\s+00:([0-9A-F]+)$',listing,re.M)
 assert match,name
 return int(match[1],16)
c2=bool(re.search(r'CUSTOM2=([1-9][0-9]*)',args))
fast=m['options']['CPU'] not in ['68000','68010']
verify=b'GPCVERIFY\0' in (root/'slave.slave').read_bytes()
for name in ['GrandPrixCircuitHD.s','simulation.s']:
 for line in (source/name).read_text().splitlines():
  if 'PERF_RANGE h0:' not in line:continue
  decl=re.search(r'PL_(PSS|PS|P) \$([0-9a-f]+),(\w+)(?:,(\d+))?\s*; PERF_RANGE h0:([0-9A-F]+) (\d+) bit=(\w+)',line)
  assert decl,line
  kind,site,target,skip,site2,span,gate=decl.groups();site=int(site,16);assert site==int(site2,16);span=int(span)
  enabled_gate=(c2 and (fast or gate=='C2')) if gate.startswith('C2') else (verify and bool(re.search(r'CUSTOM5=([1-9][0-9]*)',args)))
  if gate=='BASE':enabled_gate=True
  if gate=='VERIFY_RENDER':enabled_gate=verify and bool(custom4 & 8)
  off=h-base+site
  if enabled_gate:
   opcode='4ef9' if kind=='P' else '4eb9';written=6+int(skip or 0)
   assert d[off:off+2]==bytes.fromhex(opcode),hex(site)
   actual=struct.unpack_from('>I',d,off+2)[0]
   assert actual==rr['slave'][0]+symbol(target),(hex(site),target,hex(actual))
   assert d[off+6:off+written]==bytes.fromhex('4e71')*((written-6)//2),hex(site)
   assert d[off+written:off+span]==raw[40+site+written:40+site+span],hex(site)
   d[off:off+span]=raw[40+site:40+site+span];enabled.append(gate+' '+hex(site))
  else:assert d[off:off+span]==raw[40+site:40+site+span],hex(site)
for site,opcode in [(0x9fc2,'5383'),(0xa020,'5d83'),(0xa054,'5280')]:
 off=h-base+site
 assert d[off:off+2]==bytes.fromhex(opcode),hex(site)
 d[off:off+2]=raw[40+site:40+site+2]
 enabled.append('track address '+hex(site))
check(d,base,m['options']['CPU'])
print('Exact VERIFY patch sites:',', '.join(enabled))
# A corruption outside these sites must still be rejected.
d[h-base+0x39e]^=1
try:check(d,base,m['options']['CPU'])
except AssertionError:print('Negative control: corrupted swap instruction rejected')
else:raise AssertionError('negative control accepted')
