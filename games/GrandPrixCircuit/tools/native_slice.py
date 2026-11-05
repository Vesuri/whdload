#!/usr/bin/env python3
import re,sys
from pathlib import Path
lo,hi=[int(x,16) for x in sys.argv[1:3]]
for line in (Path(__file__).resolve().parents[1]/'tmp/phase3/native.dis').read_text().splitlines():
 m=re.match(r'\s*([0-9a-f]+):',line)
 if m and lo<=int(m[1],16)<hi:print(line)
