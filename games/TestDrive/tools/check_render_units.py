#!/usr/bin/env python3
"""Require completed native phase-10 cache and signed-product assertions."""
import argparse,json,struct
from pathlib import Path
def check(path):
 b=path.read_bytes();marker=b'TDRENDER10\0'
 assert b.count(marker)==1,'missing or ambiguous renderer results'
 pos=(b.index(marker)+len(marker)+1)&~1
 failed,count,first=struct.unpack_from('>III',b,pos)
 assert (failed,count,first)==(0,1421,0),(failed,count,first)
 return dict(status='PASS',assertions=count,failures=failed)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('dump',type=Path);a=p.parse_args()
 print(json.dumps(check(a.dump),indent=2))
