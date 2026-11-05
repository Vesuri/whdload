#!/usr/bin/env python3
"""Check disabled PERF_RANGE sites against the pristine relocated executable.
Only explicitly enabled gates are skipped, including overlaps between fixtures.
Input is a calibrated capture directory containing metadata.json/game-code.bin.
"""
import argparse,json,re,struct
from pathlib import Path
from game_image import ROOT,hunks,GAME
from capture_demo import sha
SOURCE=ROOT/'src'
def check(directory,enabled=()):
 from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
 ranges=[]
 for path in sorted(SOURCE.glob('*.s')):
  for line,txt in enumerate(path.read_text(encoding='latin1').splitlines(),1):
   m=re.search(r'PERF_RANGE\s+(\w+)\s+\$([0-9a-fA-F]+)\s+\$([0-9a-fA-F]+)',txt)
   if m:ranges.append(dict(gate=m[1],offset=int(m[2],16),size=int(m[3],16),source=path.name,line=line))
 assert ranges,'no PERF_RANGE declarations'
 assert set(enabled)<=set(r['gate'] for r in ranges),'unknown enabled gate'
 meta=json.loads((directory/'metadata.json').read_text());assert meta['game_sha256']==sha(GAME),'pristine executable changed';regions=meta['layout']['regions'];hs=hunks();pristine=bytearray(hs[0]['data']);live=(directory/'game-code.bin').read_bytes()
 assert len(live)==len(pristine),'wrong or truncated code hunk'
 for off,target in hs[0]['relocs']:
  value=struct.unpack_from('>I',pristine,off)[0]+regions[target]['base'];struct.pack_into('>I',pristine,off,value)
 dis=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);results=[]
 active=[r for r in ranges if r['gate'] in enabled]
 for r in ranges:
  off,n=r['offset'],r['size'];assert n>0 and off+n<=len(pristine)
  original=bytes(pristine[off:off+n]);ins=list(dis.disasm(original,off));assert sum(i.size for i in ins)==n,'partial instruction range'
  skip=any(off<x['offset']+x['size'] and x['offset']<off+n for x in active)
  results.append(dict(r,status='enabled/overlap' if skip else 'PASS' if live[off:off+n]==original else 'FAIL',original=original.hex(),actual=live[off:off+n].hex()))
 return dict(enabled=list(enabled),passed=all(r['status']!='FAIL' for r in results),ranges=results)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--enabled',action='append',default=[]);a=p.parse_args();result=check(a.capture,a.enabled);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
