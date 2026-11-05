#!/usr/bin/env python3
"""Read cache/check state using the exact retained VERIFY listing and live marker."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('--entry',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
marker=r.locate();b=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();base=r.DUMP_BASE;slave=marker-label('tape_marker');at=slave+label('cache_state')-base
s=b[at:at+50];real,planes,mask,wh,ps,depth,unused,block,size=struct.unpack('>5I2H2I',s[:32]);check_at=slave+label('cache_verify_header')-base;v,builds,draws=struct.unpack_from('>3I',b,check_at+8)
result=dict(route=r.read(marker),slave_base=slave,sim=r.read(marker)['sim'],cache=dict(valid=bool(block),descriptor=real,planes=planes,mask=mask,width=wh>>16,height=wh&65535,plane_size=ps,depth=depth,block=block,size=size),checks=dict(version=v,build_twins=builds,pixel_twins=draws))
if re.search(r'^cache_lifecycle_test\s',listing,re.M):result['checks']['lifecycle']=struct.unpack_from('>I',b,check_at+20)[0]
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
