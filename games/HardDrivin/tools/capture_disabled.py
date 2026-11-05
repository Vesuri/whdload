#!/usr/bin/env python3
"""Fresh-boot a slave to the native title key site and verify inactive patch ranges."""
import argparse,json,os,shutil
from pathlib import Path
from capture_demo import ROOT
from capture_session import Session
from check_disabled import check
from machine_profiles import PROFILES
p=argparse.ArgumentParser(description=__doc__);p.add_argument('out');p.add_argument('--slave',required=True,type=Path);p.add_argument('--profile',choices=PROFILES,default='a500');p.add_argument('--custom4',type=int,default=0);p.add_argument('--enabled',action='append',default=[]);a=p.parse_args();os.chdir(ROOT)
out=Path(a.out).resolve();rel=out.relative_to(ROOT/'tmp/prof');assert not any(c.isspace() for c in str(rel));out.mkdir(parents=True,exist_ok=False);shutil.copyfile(a.slave.resolve(),out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x8520,a.custom4)
try:
 s.boot();r=check(out,a.enabled);(out/'disabled.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
finally:s.close()
