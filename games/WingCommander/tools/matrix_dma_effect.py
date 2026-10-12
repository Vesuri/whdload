#!/usr/bin/env python3
"""Quantify DMA recording effects without relabelling a changed run as exactly neutral."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from matrix_scene_report import report as scene_report


def compare(control,candidate):
    runs=(control,candidate)
    metadata=[json.loads((p/'result.json').read_text()) for p in runs]
    left,right=metadata
    if left.get('dma') or not right.get('dma'):raise ValueError('DMA off/on pair required')
    for key in ('machine','options','audit_cacr','emulator_sha256','slave_sha256','hunks','slave',
                'boot_cpu','live_cpu','nommu_core','mmu_core','idle','irq_scopes','raw_chunky','profiles','host_warp'):
        if left.get(key)!=right.get(key):raise ValueError('unmatched DMA configuration: '+key)
    scenes=[scene_report(p)['scenes'] for p in runs]
    ledgers=[(p/'matrix-events.txt').read_text().splitlines() for p in runs]
    def without_clock(lines):
        result=[]
        for line in lines:
            p=line.split();del p[4 if p[0]=='B' else 3];result.append(p)
        return result
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
                records_equal_except_clock=without_clock(ledgers[0])==without_clock(ledgers[1]),
                final_game_hunks_equal=hunks,menu_pixels_equal=pixels,raw_sources_equal=raw_equal,
                maximum_absolute_scene_seconds_change=max(abs(s['seconds_change']) for s in deltas),
                scenes=deltas,scope='Measured recording effect; DMA slots describe the instrumented run.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control',type=Path);parser.add_argument('candidate',type=Path)
    args=parser.parse_args();print(json.dumps(compare(args.control,args.candidate),indent=2))
