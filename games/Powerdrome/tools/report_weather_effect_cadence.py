#!/usr/bin/env python3
"""Measure original A500 effect episodes from generation and lifetime probes.

Reports mutation/draw-entry timing, not visible scanout duration. Rejects captures
with the experimental effect renderer hook installed.
"""
import argparse
import json
from pathlib import Path
import re
from statistics import mean, median
from weather_state import parse_values
from weather_effect_state import locate


def summary(values):
    return {'count':len(values),'mean_ms':mean(values),'median_ms':median(values),
            'minimum_ms':min(values),'maximum_ms':max(values),
            'histogram_ms':{str(v):values.count(v) for v in sorted(set(values))}}


def report(root):
    chip=(root/'chip.bin').read_bytes();code=(root/'code.bin').read_bytes()
    game=int((root/'game-base.txt').read_text(),0);base=int((root/'dump-base.txt').read_text(),0)
    assert locate(chip,code,game,base) is None, 'Requires native lifetime ownership'
    config=json.loads((root/'configuration.json').read_text())
    assert config['CPU']=='68000', 'This report is the original A500 calibration'
    events=[(int(f),int(o,16),parse_values(v)) for f,o,v in re.findall(
        r'^PDWEATHER_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
        (root/'swaps-gdb.txt').read_text(),re.M)]
    episodes=[];pending=None;interrupted=[];zero=0
    for field,off,state in events:
        if off==0xbd16:
            if pending is not None:interrupted.append(pending)
            life=state['effect_lifetime']
            pending={'lifetime':life,'field':field,'clock':state['clock'],'draws':[]} if life else None
            zero+=int(life==0)
        elif off==0x112e6 and state['effect_lifetime']:
            assert pending is not None, 'Draw lacks its generation observation'
            index=len(pending['draws'])
            assert state['effect_lifetime']==pending['lifetime']-index
            if index:assert state['loop']==pending['draws'][-1]['loop']+1
            pending['draws'].append({'field':field,'clock':state['clock'],'loop':state['loop']})
        elif off==0x112f0 and state['effect_lifetime']==0 and pending is not None:
            assert len(pending['draws'])==pending['lifetime']
            episodes.append(pending);pending=None
    assert episodes
    field_gaps=[];clock_gaps=[]
    for e in episodes:
        for a,b in zip(e['draws'],e['draws'][1:]):
            field_gaps.append((b['field']-a['field'])*20)
            clock_gaps.append((b['clock']-a['clock'])*5)
    # BD1A follows generation. Its lifetime describes the upcoming rendered scene,
    # so group the next loop interval by this published state, not the next one.
    loops=[(f,s) for f,off,s in events if off==0xbd1a]
    generation={False:[],True:[]}
    for a,b in zip(loops,loops[1:]):
        if all(s['effects_enabled'] and s['transition']==0 and s['gate_104']==0 for _,s in (a,b)):
            assert b[1]['loop']==a[1]['loop']+1
            generation[bool(a[1]['effect_lifetime'])].append((b[0]-a[0])*20)
    return {'capture':root.name,'scope':'Native mutation/draw-entry cadence, not scanout',
            'complete_episodes':len(episodes),'zero_lifetime_selections':zero,
            'generation_intervals_without_effect':summary(generation[False]),
            'generation_intervals_with_effect':summary(generation[True]),
            'interrupted_episodes':len(interrupted),'pending_episode':pending is not None,
            'draws':sum(len(e['draws']) for e in episodes),
            'within_episode_field_intervals':summary(field_gaps),
            'within_episode_clock_intervals':summary(clock_gaps),
            'generation_to_first_draw_fields':summary([(e['draws'][0]['field']-e['field'])*20 for e in episodes]),
            'generation_to_last_decrement_fields':{
                str(life):summary([(e['draws'][-1]['field']-e['field'])*20 for e in episodes if e['lifetime']==life])
                for life in sorted({e['lifetime'] for e in episodes})}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    print(json.dumps(report(p.parse_args().capture),indent=2))
