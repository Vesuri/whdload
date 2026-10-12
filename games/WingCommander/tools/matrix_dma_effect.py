#!/usr/bin/env python3
"""Quantify DMA or callback recording effects without claiming exact neutrality."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from matrix_scene_report import report as scene_report


def compare(control,candidate,feature="dma"):
    if feature not in ("dma", "irq_scopes"):raise ValueError("unsupported recording feature")
    runs=(control,candidate)
    metadata=[json.loads((p/'result.json').read_text()) for p in runs]
    left,right=metadata
    if left.get(feature) or not right.get(feature):raise ValueError(feature+' off/on pair required')
    for key in ('machine','options','audit_cacr','emulator_sha256','slave_sha256','hunks','slave',
                'boot_cpu','live_cpu','dma','nommu_core','mmu_core','idle','irq_scopes', 'irq_trace', 'irq_beam','raw_chunky','profiles','host_warp'):
        if key == feature:continue
        if left.get(key, False if key in ("irq_scopes", "irq_trace", "irq_beam") else None) != right.get(key, False if key in ("irq_scopes", "irq_trace", "irq_beam") else None):raise ValueError('unmatched recording configuration: '+key)
    scenes=[scene_report(p)['scenes'] for p in runs]
    ledgers=[(p/'matrix-events.txt').read_text().splitlines() for p in runs]
    def without_clock(lines):
        result=[]
        for line in lines:
            p=line.split();del p[4 if p[0]=='B' else 3];result.append(p)
        return result
    same_events=without_clock(ledgers[0])==without_clock(ledgers[1])
    without_fields=[]
    for lines in ledgers:
        rows=[]
        for line in lines:
            row=line.split()
            # Remove timing fields together; keep event kind, scene and payload.
            start=3 if row[0]=='B' else 2
            del row[start:start+2];rows.append(row)
        without_fields.append(rows)
    same_payload=without_fields[0]==without_fields[1]
    clock_deltas=[];field_deltas=[]
    if same_payload:
        for a,b in zip(*ledgers):
            x,y=a.split(),b.split();index=4 if x[0]=='B' else 3
            clock_deltas.append(int(y[index])-int(x[index]))
            field_deltas.append(int(y[index-1])-int(x[index-1]))
    memories=[(p/'fast.bin').read_bytes() for p in runs]
    hunks=[]
    for base,size in zip(left['hunks'],(0x35ea4,0xfda0,4,0x1590)):
        at=base-0x200000
        hunks.append(memories[0][at:at+size]==memories[1][at:at+size])
    with Image.open(control/'menu.png') as a,Image.open(candidate/'menu.png') as b:
        pixels=a.size==b.size and a.convert('RGB').tobytes()==b.convert('RGB').tobytes()
    raw_equal=None
    if left.get('raw_chunky'):
        def digest(path):
            h=hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            return h.hexdigest()
        raw_equal=digest(control/'chunky-sources.bin')==digest(candidate/'chunky-sources.bin')
    deltas=[dict(scene=a['scene'],seconds_change=b['seconds']-a['seconds'],
                 publications_change=b['publications']-a['publications'],fields_change=b['fields']-a['fields'])
            for a,b in zip(*scenes)]
    return dict(ledger_exact=ledgers[0]==ledgers[1],
                records_equal_except_clock=same_events,
                records_equal_except_clock_and_field=same_payload,
                changed_field_records=sum(d!=0 for d in field_deltas) if same_payload else None,
                maximum_absolute_field_change=max(map(abs,field_deltas),default=0) if same_payload else None,
                changed_clock_records=sum(d!=0 for d in clock_deltas) if same_payload else None,
                maximum_absolute_event_seconds_change=max(map(abs,clock_deltas),default=0)/(512*3546895) if same_payload else None,
                final_game_hunks_equal=hunks,menu_pixels_equal=pixels,raw_sources_equal=raw_equal,
                maximum_absolute_scene_seconds_change=max(abs(s['seconds_change']) for s in deltas),
                scenes=deltas,scope='Measured recording effect; '+feature+' measurements describe the instrumented run.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control',type=Path);parser.add_argument('candidate',type=Path)
    parser.add_argument('--feature',choices=('dma','irq_scopes'),default='dma')
    args=parser.parse_args();print(json.dumps(compare(args.control,args.candidate,args.feature),indent=2))
