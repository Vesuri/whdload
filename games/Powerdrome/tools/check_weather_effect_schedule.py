#!/usr/bin/env python3
"""Verify 80/140-ms weather loops and the +20-ms visual phase from world-step probes.

Checks the seeded mode-2 first episode and all observed scheduled mutations.
Draw ownership/pixels and mode lifecycle validation require separate checks.
"""
import argparse
from pathlib import Path
import re
import struct
from report_weather import advance_seed
from weather_effect_state import locate, parse_values as effect_values, snapshot as effect_snapshot
from weather_effect_clock import parse_values as clock_values, snapshot as clock_snapshot


def check(root,seeded=True):
    text=(root/'swaps-gdb.txt').read_text()
    def events(tag,parser):
        return [(int(f),parser(v)) for f,v in re.findall(
            rf'^{tag} (-?\d+) 0xccee (.+)$',text,re.M)]
    clocks=events('PDWECLK_EVENT',clock_values)
    effects=events('PDWEFX_EVENT',effect_values)
    worlds=events('PDW20_EVENT',lambda v:list(map(int,v.split())))
    assert clocks and len(clocks)==len(effects)==len(worlds)
    previous=None;timeline={};generation_rows={};visual_rows={}
    for (field,c),(efield,e),(wfield,w) in zip(clocks,effects,worlds):
        assert field==efield==wfield
        now=w[0]
        assert c['initialized']==1
        assert c['generations']==e['ticks']
        assert c['generations']-c['publications']==c['pending'] in (0,1)
        assert c['period'] in (16,28)
        assert c['next_generation']==c['generation_clock']+c['period']
        assert c['visual_deadline']==c['generation_clock']+4
        assert c['visual_clock']==e['clock']
        if previous is not None:
            pc,pe,pnow=previous
            assert now==pnow+4, 'Missing world-step observation'
            dg=c['generations']-pc['generations'];dv=c['publications']-pc['publications']
            assert (dg,dv) in ((0,0),(1,0),(0,1)), 'Dropped/repeated weather boundary'
            if dg:
                assert c['generation_clock']==now-4==pc['next_generation'], 'Generation ran off deadline'
                assert c['pending']==1
                assert c['period']==(28 if e['lifetime'] else 16)
                assert all(e[k]==pe[k] for k in ('visible','visual_seed','clock','visual_events'))
                generation_rows[c['generation_clock']]=(c,e)
                timeline[('g',c['generation_clock'])]=(c['period'],e['lifetime'],e['delay'],e['attempts'],e['selections'],c['generation_seed'])
            elif dv:
                assert c['visual_clock']==now-4==pc['visual_deadline'], 'Visual publication ran off deadline'
                assert c['pending']==0
                assert e['visible']==pe['lifetime'] and e['lifetime']==max(0,pe['lifetime']-1)
                assert e['delay']==pe['delay']
                assert e['visual_events']==pe['visual_events']+int(e['visible']>0)
                if e['visible']:
                    assert c['visual_after_seed']==advance_seed(e['visual_seed'],4), 'Wrong logical visual RNG advance'
                visual_rows[c['visual_clock']]=(c,e)
                timeline[('v',c['visual_clock'])]=(e['visible'],e['lifetime'],e['delay'],e['visual_events'],e['visual_seed'],c['visual_after_seed'])
            else:
                assert all(c[k]==pc[k] for k in c), 'Weather clock changed outside a scheduled boundary'
                assert all(e[k]==pe[k] for k in ('visible','visual_seed','clock','visual_events','lifetime','delay','attempts','selections'))
        previous=(c,e,now)
    code=(root/'final-code.bin').read_bytes();chip=(root/'final-chip.bin').read_bytes()
    game=int((root/'game-base.txt').read_text(),0);base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert code[address-base:address-base+8] == b'PDWEFX03'
    start=clock_snapshot(root)['generation_clock']
    if seeded:
        tag=code.find(b'PDWEFT01',address-base+48,address-base+4096)
        assert tag>=0
        count,step,start=struct.unpack_from('>3I',code,tag+8)
        assert count==1 and step>=200
        c,e=generation_rows[start]
        assert (c['generation_seed'],e['lifetime'],e['delay'],e['attempts'],e['selections'])==(51585,5,7,1,1)
        for n in range(5):
            c,e=visual_rows[start+4+28*n]
            assert (e['visible'],e['lifetime'],e['delay'],e['visual_events'])==(5-n,4-n,7-n,n+1)
            assert e['attempts']==e['selections']==1
        c,e=generation_rows[start+140]
        assert c['period']==16 and e['visible']==1 and e['lifetime']==0, 'Last visible state was not retained until the next visual phase'
        c,e=visual_rows[start+144]
        assert e['visible']==e['lifetime']==0 and e['visual_events']==5
        c,e=generation_rows[start+172]
        assert e['attempts']==2, 'Generation delay did not release the next trial at 860 ms'
    final=effect_snapshot(root,True);phase=clock_snapshot(root,True)
    assert final['drawing']==0, 'Capture ended inside effect draw; finish ownership check separately'
    worlds=[i for i in range(len(code)-24) if code[i:i+8]==b'PDW20T01'
            and struct.unpack_from('>H',code,i+8)[0]==1]
    assert len(worlds)==1
    cursor=struct.unpack_from('>I',code,worlds[0]+12)[0]
    assert phase['next_generation']>=cursor, 'Unserved overdue generation at endpoint'
    if phase['pending']:
        assert cursor<=phase['visual_deadline']<phase['next_generation'], 'Unserved overdue visual phase at endpoint'
    assert phase['generations']-phase['publications']==phase['pending'] in (0,1)
    print(f'{root.name}: {len(generation_rows)} observed generation boundaries and {len(visual_rows)} visual boundaries on exact world deadlines')
    if seeded:print('  First five-step effect: first publication 20 ms, last decrement 580 ms, clear 720 ms; next trial 860 ms')
    print(f'  Final selections={final["selections"]}, logical visual events={final["visual_events"]}, draws={final["draws"]}; scheduled future visual={phase["pending"]}')
    return {(kind,clock-start):values for (kind,clock),values in timeline.items()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    p.add_argument('--general',action='store_true',help='Check schedule invariants without requiring the seeded mode-2 first episode')
    args=p.parse_args()
    results=[check(root,seeded=not args.general) for root in args.captures]
    common=set.intersection(*(set(r) for r in results))
    assert common
    for key in common:assert all(r[key]==results[0][key] for r in results), f'CPU schedule/state mismatch at {key}'
    print(f'{len(common)} common generation/visual states match across supplied captures; draw ownership and full-cycle/lifecycle checks remain separate.')
