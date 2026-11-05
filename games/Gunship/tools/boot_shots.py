#!/usr/bin/env python3
"""Boot the game in warp and save a screenshot every STEP fields: boot_shots.py OUT FIELDS STEP."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session
out,total,step=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
s=Session(out)
try:
    while s.field<total:
        s.fields(step);print(s.field,s.shot(f'f{s.field:05d}.png'),flush=True)
finally:s.quit()
