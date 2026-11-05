#!/usr/bin/env python3
"""Rendering ledger: exact clocks, converter elapsed service time and scene durations."""
import argparse, collections, json, re, statistics
from pathlib import Path
from PIL import Image, ImageChops
from intro_timing_report import report as timing_report


def report(run):
    meta=json.loads((run/'result.json').read_text()); result=timing_report(run, strict_tod=False)
    result['fixture']=meta['fixture']; result['verified_frames']=meta['verified_frames']
    s=meta['slave'];syms=meta['symbols'];events=[]
    for line in (run/'events.txt').read_text().splitlines():
        if line.startswith('#'):continue
        events.append([int(v,16 if i==0 or 8<=i<24 else 10) for i,v in enumerate(line.split())])
        if events[-1][0]==meta['hunks'][0]+0x20214: break
    twin=meta['fixture'].get('render_verify',False)
    enabled='CUSTOM1=2' in meta['options'].upper().split() and meta['fixture']['render']
    entries={s+syms[f'kalms_{cpu}_{height}']:height for cpu in ('030','040') for height in (128,166,200)} if enabled else {s+off:height for off,height in ((0x17f6,128),(0x195e,166),(0x1ac6,200))}
    if enabled and meta.get('selected_converter')==0:
        entries={s+off:height for off,height in ((0x17f6,128),(0x195e,166),(0x1ac6,200))}
    result['selected_converter']=meta.get('selected_converter')
    end=s+syms['render_converted'] if enabled else s+0x17a6
    samples=collections.defaultdict(list); pending=None; sources=set(); dests=set();wait=None; waits=[];wait_lines=[];reference_region=False
    for e in events:
        if e[0] in entries and not reference_region:
            if pending is not None: raise ValueError('nested converter')
            pending=e; sources.add(e[16]); dests.add(e[17])
            assert 0x200000<=e[16]<0xa00000, 'chunky source outside FAST'
            assert 0<e[17]<0x200000 and e[17]%8==0, 'unaligned/non-CHIP destination'
        elif e[0]==end:
            if pending is None:raise ValueError('converter return without entry')
            samples[entries[pending[0]]].append((e[3]-pending[3])/(512*3546895)*1000)
            pending=None; reference_region=twin
            if e[0]==s+syms['render_wait']: wait=e
        elif e[0]==s+syms['render_wait']:wait=e
        elif e[0]==s+syms['render_wait_done']:
            if wait is None:raise ValueError('wait return without entry')
            waits.append((e[3]-wait[3])/(512*3546895)*1000);wait_lines.append(e[4]);wait=None;reference_region=False
    if pending is not None or wait is not None:raise ValueError('unfinished converter/wait')
    result['converter_elapsed_ms']={height:dict(count=len(values),minimum=min(values),median=statistics.median(values),maximum=max(values)) for height,values in samples.items()}
    if not samples:raise ValueError('no conversions')
    result['performance_eligible']=not twin
    result['fast_source_addresses']=len(sources); result['aligned_chip_destinations']=len(dests)
    result['wait_ms']=dict(count=len(waits),median=statistics.median(waits),maximum=max(waits),return_lines=sorted(set(wait_lines))) if waits else None
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--control',type=Path);a=p.parse_args()
    result=report(a.run)
    if a.control:
        control=report(a.control)
        if not result['performance_eligible'] or not control['performance_eligible']:raise ValueError('native twin cannot measure performance')
        cacr=lambda r:re.search(r'cacr=(\w+)',r['live_cpu'])[1]
        if cacr(result)!=cacr(control):raise ValueError('unmatched cache state')
        if re.sub(r'cacr=\w+','',result['live_cpu'])!=re.sub(r'cacr=\w+','',control['live_cpu']):raise ValueError('unmatched CPU backend')
        result['comparison']={h:dict(control_ms=control['converter_elapsed_ms'][h]['median'],render_ms=v['median'],reduction_percent=100*(1-v['median']/control['converter_elapsed_ms'][h]['median'])) for h,v in result['converter_elapsed_ms'].items()}
        with Image.open(a.run/'menu.png') as x, Image.open(a.control/'menu.png') as y:
            x=x.convert('RGB'); y=y.convert('RGB')
            result['menu_pixels_equal']=x.size==y.size and ImageChops.difference(x,y).getbbox() is None
        if not result['menu_pixels_equal']: raise ValueError('menu pixels differ')
        result['performance_nonregression']=all(v['reduction_percent']>=0 for v in result['comparison'].values())
        if [x['scene'] for x in control['scenes']]!=[x['scene'] for x in result['scenes']]: raise ValueError('scene sequence changed')
        result['scene_deltas']=[dict(scene=x['scene'],seconds=y['seconds']-x['seconds'],control_seconds=x['seconds'],render_seconds=y['seconds']) for x,y in zip(control['scenes'],result['scenes'])]
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
