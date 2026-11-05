#!/usr/bin/env python3
"""Read the actual VERIFY assembly assertion result from a saved RAM capture."""
import argparse,json,struct
from pathlib import Path
MARK=b'TDVERIFY7\0'
def check(raw, expected_count=22):
 assert raw.count(MARK)==1,'missing/ambiguous VERIFY marker'
 at=raw.index(MARK)+len(MARK);at=(at+1)&~1
 failed,count,first=struct.unpack_from('>III',raw,at)
 assert count==expected_count,('assertions did not finish',count)
 assert failed==first==0,('assembly assertion failed',failed,first)
 return dict(status='PASS',assertions=count,result_offset=at)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('ram',type=Path);a=p.parse_args();print(json.dumps(check(a.ram.read_bytes()),indent=2))
