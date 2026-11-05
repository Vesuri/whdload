#!/usr/bin/env python3
"""Run a scripted input route: route.py OUT STEP...

Steps: f:N (advance N fields), t:KEY[:N] (tap KEY, held N fields, default 4),
d:KEY / u:KEY (press / release), s:NAME (screenshot NAME.png), S:N:EVERY (N fields with a shot
every EVERY), m:DX:DY (mouse move), c[:N] (left click, held N fields), p:N:FILE (profile N fields into FILE, relative to OUT).
KEY is a gunship.KEYS name or a hex raw code.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session,KEYS
def key(k):return k if k in KEYS else int(k,16)
def run(s,steps):
    for st in steps:
        op,*a=st.split(':')
        if op=='f':s.fields(int(a[0]))
        elif op=='t':
            s.key(key(a[0]),1);s.fields(int(a[1]) if len(a)>1 else 4);s.key(key(a[0]),0)
        elif op=='d':s.key(key(a[0]),1)
        elif op=='u':s.key(key(a[0]),0)
        elif op=='s':s.shot(a[0]+'.png')
        elif op=='S':
            n,e=int(a[0]),int(a[1])
            for i in range(0,n,e):s.fields(e-1);s.shot(f'f{s.field:05d}.png')
        elif op=='m':s.mouse(int(a[0]),int(a[1]))
        elif op=='c':s.click(hold=int(a[0]) if a else 4)
        elif op=='p':s.profile(int(a[0]),s.out/a[1])
        else:raise ValueError(st)
        print(s.field,st,flush=True)
if __name__=='__main__':
    s=Session(sys.argv[1],{})
    try:run(s,sys.argv[2:])
    finally:s.quit()
