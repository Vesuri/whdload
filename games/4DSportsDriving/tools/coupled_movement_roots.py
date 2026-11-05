#!/usr/bin/env python3
"""Exhaustively inspect published-pitch roots for cycling coupling cases."""
import json
from coupled_movement_check import ROOT,r,correction,predict
source=json.loads((ROOT/'tmp/prof/coupled-movement-check.json').read_text())
entries={e[0]:e for e in r['ENTRY']};results=[]
for case in source['rows']:
    if case['status']!='cycle':continue
    entry=entries[case['tick']];roots=[];unsupported=0;tested=0;near=[]
    # tilt() wraps its intermediate angle into [-512,512], then subtracts256.
    for pitch in range(-768,257):
        try:out=predict(entry,correction(entry,pitch))
        except Exception:unsupported+=1;continue
        tested+=1
        if out['pitch']==pitch:roots.append(pitch)
        if abs(out['pitch']-pitch)<=2:near.append([pitch,out['pitch']])
    results.append(dict(tick=entry[0],roots=roots,tested=tested,unsupported=unsupported,near=near))
report=dict(cases=results,scope='All1025 integers spanning predictor published-pitch output range enumerated for five cycling recorded starts. Unsupported contact/query domains cannot be assessed. Zero correction carry, current starting state only; not a corrected trajectory.')
(ROOT/'tmp/prof/coupled-movement-roots.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
