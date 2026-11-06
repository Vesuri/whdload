#!/usr/bin/env python3
"""Differing ranges between two dump_run.py dumps: mem_diff.py A/sNNNN B/sNNNN [GAP]

Prints chip ranges and image ranges (g:$ numbering) that differ, merging differences closer
than GAP bytes (default 16), with state_run.py's EXCLUDE regions marked."""
import sys
from state_run import EXCLUDE
def ranges(a,b,gap):
    out=[];i=0;n=min(len(a),len(b))
    while i<n:
        if a[i]!=b[i]:
            j=i;last=i
            while j<n and j-last<=gap:
                if a[j]!=b[j]:last=j
                j+=1
            out.append((i,last+1));i=last+1
        else:i+=1
    return out
def note(kind,lo,hi):
    for k,a,b,why in EXCLUDE:
        if k==kind and lo<b and hi>a:return f'  [excluded: {why}]'
    return ''
if __name__=='__main__':
    A,B=sys.argv[1],sys.argv[2];gap=int(sys.argv[3]) if len(sys.argv)>3 else 16
    for ext,kind,base,fmt in (('chip','chip',0,'${:05x}'),('img','g',0x1000,'g:${:05x}')):
        a=open(f'{A}.{ext}','rb').read();b=open(f'{B}.{ext}','rb').read()
        for lo,hi in ranges(a,b,gap):
            print(f'{fmt.format(lo+base)}-{fmt.format(hi+base)} ({hi-lo} bytes){note(kind,lo+base,hi+base)}')
