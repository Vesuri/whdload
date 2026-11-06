#!/usr/bin/env python3
"""Boot and take a screenshot every STEP fields: explore.py OUT STEP COUNT"""
import sys
from pop import Session
out,step,count=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
s=Session(out,{})
try:
    for i in range(count):
        s.fields(step);s.shot(f'f{s.field:05d}.png');print(s.field,flush=True)
finally:s.quit()
