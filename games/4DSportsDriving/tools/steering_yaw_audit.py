#!/usr/bin/env python3
"""Reproduce native heading lookup and quantify observed quantization loss.

Continuous angles diagnose existing traces; they do not predict a changed
closed-loop trajectory and are not a replacement acceptance criterion.
"""
import hashlib,json,math,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
code=raw[0x28:];base=0x3a1dc+0x7ffe
table=raw[base-0x386c:base-0x386c+257]
assert struct.unpack_from('>8I',raw,base-0x388c)==(0x30500,0x304fa,0x3050c,0x30506,0x30514,0x30518,0x30526,0x3051e)
assert code[0x304cc:0x304d6].hex()=='484182c29442e049d342'

def native(x,y):
    # 3049C: absolute operands, octant swap, ratio rounded to nearest /256,
    # byte angle table, then the exact eight signed quadrant transforms.
    octant=(4 if x<0 else 0)+(2 if y<0 else 0)
    x,y=abs(x),abs(y)
    if x==y:
        if not x:return 0
        angle=128
    else:
        if x>y:x,y=y,x;octant+=1
        quotient=(x<<16)//y
        angle=table[(quotient>>8)+((quotient>>7)&1)]
    return (angle,256-angle,512-angle,256+angle,-angle,angle-256,angle-512,-256-angle)[octant]

def delta(angle):return (angle+512)%1024-512
report=dict(executable_sha256=hashlib.sha256(raw).hexdigest(),lookup_sha256=hashlib.sha256(code[0x3049c:0x3052c]).hexdigest(),rates={})
for hz in (20,50):
    path=root/f'tmp/prof/steering-yaw{hz}/yaw-probe.json'
    rows=json.loads(path.read_text())['rows']
    for row in rows:
        assert native(row['x'],-row['z'])==row['new_heading'],row
        assert row['spin']==0,row
    right=rows[:hz//2]
    continuous=sum(delta(math.atan2(r['x'],-r['z'])*512/math.pi-r['old_heading']) for r in right)
    applied=sum(delta(r['new_heading']-r['old_heading']) for r in right)
    report['rates'][hz]=dict(trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),exact_lookup_matches=len(rows),right_turn_steps=len(right),continuous_delta_sum=continuous,applied_delta_sum=applied,discarded_delta_sum=continuous-applied)
report['scope']='Exact native lookup reproduction for every captured call; continuous-angle sum diagnoses quantization on the observed path, not a corrected closed-loop prediction.'
(root/'tmp/prof/steering-yaw-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
