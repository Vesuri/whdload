#!/usr/bin/env python3
"""Negative controls against retained real captures; never modify evidence files."""
import json
from harness import ROOT
import compare_simulation_demo as c
A=ROOT/'tmp/phase8/visual-verge-demo-a500';B=ROOT/'tmp/phase8/visual-verge-demo-a1200'
assert c.compare(A,B)['status']=='PASS'
original_load=c.load

def wrong_phase(p):
 m,s=original_load(p)
 if p==A:s[min(s)]['background_phase']='changed'
 return m,s
c.load=wrong_phase
assert c.compare(A,B)['status']=='FAIL'
c.load=original_load

def wrong_speed(p):
 m,s=original_load(p)
 if p==A:s[min(s)]['speed']+=1
 return m,s
c.load=wrong_speed
assert c.compare(A,B)['status']=='FAIL'
c.load=original_load

def different_snapshot(p):
 m,s=original_load(p)
 if p==A:s[min(s)]['saved_x']+=1
 return m,s
c.load=different_snapshot
snapshot_result=c.compare(A,B)
assert snapshot_result['status']=='PASS'
assert snapshot_result['drawing_snapshots']['saved_x_first_difference'] is not None
c.load=original_load
original_private=c.private
calls=0

def wrong_rng(raw):
 global calls
 r=original_private(raw);calls+=1
 if calls==1:r['rng_log'][0],r['rng_log'][1]=r['rng_log'][1],r['rng_log'][0]
 return r
c.private=wrong_rng
assert c.compare(A,B)['status']=='FAIL'
c.private=original_private
original_wind=c.wind

def wrong_effect(p,m):
 r=original_wind(p,m)
 if p==A:r[0][0]+=1
 return r
c.wind=wrong_effect
assert c.compare(A,B)['status']=='FAIL'
c.wind=original_wind
print(json.dumps(dict(status='PASS',rejected=['background phase divergence','vehicle speed divergence','gameplay RNG reorder','windscreen position divergence'])))
