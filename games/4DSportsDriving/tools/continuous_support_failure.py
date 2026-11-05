#!/usr/bin/env python3
"""Reconstruct the exact first unsupported live state from saved callbacks."""
import ast,json,math
from pathlib import Path
from continuous_support_reference import integrate
from coupled_contact_reference import Unsupported
p=Path('tmp/prof/continuous-support-ordered');tree=ast.parse(Path('tools/continuous_support_ordered_live.py').read_text())
names=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in n.targets))+('car_pointer',)
prior={};res=[0.]*4;count=0
for line in (p/'callback.txt').read_text().splitlines():
    if line.startswith('RESET '):res[int(line.split()[1])]=0.
    if not line.startswith('SELECT '):continue
    r=dict(zip(names,map(int,line.removeprefix('SELECT ').split())));w=r['wheel']
    if w in prior:
        entry=dict(r);entry['velocity']+=res[w]
        try:out=integrate(entry,prior[w])
        except Unsupported as error:
            report=dict(completed_interventions=count,input=entry,previous=prior[w],host_velocity_residual=res[w],reason=str(error),events=getattr(error,'events',[]),scope='Exact replay of first unsupported live callback. Earlier writes verified in callback.txt; no whole-trajectory result or handling acceptance.')
            (p/'unsupported.json').write_text(json.dumps(report,indent=2)+'\n');print('failure',r['tick'],w,'after',count,'writes',str(error));print('events',report['events'][:3],report['events'][-2:]);break
        res[w]=out['velocity']-math.floor(out['velocity']*5+1e-10)/5;count+=1
    prior[w]=r
else:raise AssertionError('Did not reproduce live failure')
