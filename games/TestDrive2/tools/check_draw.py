#!/usr/bin/env python3
"""Read runtime original/patched shape pixel and carry checks; never writes target."""
import argparse, os, struct
from pathlib import Path
from td2_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("capture",type=Path)
p.add_argument("--base",type=lambda s:int(s,0),default=0xc00000)
a=p.parse_args()
os.environ["SLAVE"]=str((a.capture/"slave.slave").resolve())
b=(a.capture/"code.bin").read_bytes()
lo,hi,_=next((lo,hi,o) for lo,hi,name,o in regions(b,a.base) if name=="slave")
marker=b"TD2DRAWCHK\0"
pos=b.find(marker,lo-a.base,hi-a.base)
assert pos>=0,"no draw verification marker"
failures,cases,first=struct.unpack_from(">III",b,(pos+len(marker)+1)&~1)
print(f"Shape twins: {cases} calls, {failures} mismatches; first differing long at byte+1={first}")
assert cases>0 and failures==0,"drawing twins did not pass"
