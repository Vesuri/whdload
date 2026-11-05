#!/usr/bin/env python3
"""Logged debugger-native input; no host UI events or guest memory writes."""
import json,sys,time
from pathlib import Path
from td import server,ROOT
LOG=Path(ROOT)/'tmp/phase3/input-actions.jsonl'
def request(s):
    reply=server.request(s)
    with LOG.open('a') as f:f.write(json.dumps({'time':time.time(),'command':s,'reply':reply})+'\n')
    if any(x in reply for x in ('ERROR','error','not supported')):raise RuntimeError(reply)
    return reply
def key(k,down):return request(f'gdb monitor key {k:x} {int(down)}')
def fields(n):return request(f'gdb monitor fields {n}')
def tap(k,n=10):
    key(k,True)
    try:fields(n)
    finally:key(k,False)
    fields(20)
if __name__=='__main__':
    request('stop')
    for arg in sys.argv[1:]:
        op,val=arg.split(':',1)
        if op=='tap':
            bits=val.split(',');tap(int(bits[0],16),int(bits[1]) if len(bits)>1 else 10)
        elif op=='down':key(int(val,16),True)
        elif op=='up':key(int(val,16),False)
        elif op=='fields':fields(int(val))
        elif op=='shot':print(request('shot '+str(Path(ROOT)/'tmp/phase3'/val)))
        else:raise ValueError(op)
