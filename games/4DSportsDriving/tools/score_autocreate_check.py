#!/usr/bin/env python3
"""Verify actual native fallback behavior and on-disk record preservation."""
import argparse,hashlib,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--missing',action='store_true');p.add_argument('--saved-dir',type=Path,default=Path('tmp/run/default/.run/dh1/data'));a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();meta=json.loads((a.capture/'anchor.json').read_text())
sym={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
at=b.index(b'4DSCRECS');base=at+12-sym['sim_score_record_status'];status,loads,resets=struct.unpack_from('>III',b,at+12)
assert (status,loads,resets)==((1,2,1) if a.missing else (3,2,0)),(status,loads,resets)
q=base+sym['sim_score_autocreate_test_count'];assert struct.unpack_from('>II',b,q)==(1,0 if a.missing else 255)
q=base+sym['sim_score_load_test_count'];assert struct.unpack_from('>II',b,q)==(1,1)
assert struct.unpack_from('>7Q',b,at+24)==(0xffffffffffffffff,)*7
native=(a.saved_dir/'Default.Hig').read_bytes()
if a.missing:
 side=(a.saved_dir/'Default.hix').read_bytes()
 import zlib
 assert len(native)==364 and len(side)==440
 assert side[:8]==b'4DHIG100' and side[20:384]==native
 assert struct.unpack_from('>I',side,16)[0]==zlib.crc32(side[20:])
 assert struct.unpack_from('>7Q',side,384)==(0xffffffffffffffff,)*7
 assert all(struct.unpack_from('>H',native,i*52+50)[0]==65535 for i in range(7))
 (a.capture/'created.hix').write_bytes(side)
else:
 original=(Path(meta['settings']['GAME'])/'data/Default.Hig').read_bytes()
 assert native==original
 assert not (a.saved_dir/'Default.hix').exists()
(a.capture/'checked.hig').write_bytes(native)
result={'status':status,'loads':loads,'resets':resets,'record_insertion_disabled':not a.missing,'native_bytes':len(native),'sha256':hashlib.sha256(native).hexdigest(),'missing_created':a.missing}
if 'sim_score_open_test_passed' in sym:
 q=base+sym['sim_score_open_test_passed'];assert struct.unpack_from('>I',b,q)[0]==6;result['open_error_cases']=6
(a.capture/'autocreate-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
