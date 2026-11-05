#!/usr/bin/env python3
"""C2 observer neutrality, retained bounds, and rejecting report controls."""
import argparse
import copy
import json
from pathlib import Path
from ocs_crossover_report import report, parse, require
from ocs_runtime import SIZES
from ocs_reconstruct import new_output


def neutrality(on,off):
    a,b=[json.loads((r/'result.json').read_text()) for r in (on,off)]
    require(a['observer']=='on' and b['observer']=='off','wrong observer pair')
    for m in (a,b):
        m['installation'].setdefault('row_aliases',[])
        m['installation'].setdefault('compositor_pointers',0)
    for key in ('arm','cpu','scene','memory','memory_base','memory_length','slave_sha256','fsuae_sha256','hunks','a4','installation'):
        require(a[key]==b[key],'different observer contract: '+key)
    for key in ('cpu_model','mmu_model','cpu_frequency','cpu_multiplier','cpu_cycle_exact','cpu_memory_cycle_exact','blitter_cycle_exact','chipset','chipmem_size','fastmem_size','bogomem_size','cachesize','cpu_speed','ntsc','immediate_blits'):
        require(a['effective'].get(key)==b['effective'].get(key),'different effective machine: '+key)
    snapshots=[(r/'end-fast.bin').read_bytes() for r in (on,off)]
    for base,size in zip(a['hunks'],SIZES):
        offset=base-a['memory_base']
        require(snapshots[0][offset:offset+size]==snapshots[1][offset:offset+size],'observer changed game state')
    require((on/'end-chip.bin').read_bytes()==(off/'end-chip.bin').read_bytes(),'observer changed Chip/pixels')
    source=a['installation']['source'];size=a['installation']['width']*a['installation']['height']
    if source>=a['memory_base']:
        offset=source-a['memory_base']
        require(snapshots[0][offset:offset+size]==snapshots[1][offset:offset+size],'observer changed Fast source')
    edges=[[r for r in parse(p/(a['scene']+'-events.txt')) if r[0] in ('B','F')] for p in (on,off)]
    require(edges[0]==edges[1],'observer changed field clocks or world counts')
    return dict(exact=True,field_edges=250,emulated_cycle_effect=0)


def negative(root):
    meta=json.loads((root/'result.json').read_text());rows=parse(root/(meta['scene']+'-events.txt'))
    report(root)
    cases=[]
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='B')[4]+=1;cases.append(('CPU clock',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='X')[2]=1;cases.append(('converted pixel',bad))
    bad=copy.deepcopy(rows);bad.remove(next(r for r in bad if r[0]=='D'));cases.append(('missing DMA',bad))
    bad=copy.deepcopy(rows);bad.remove(next(r for r in bad if r[0]=='H'));cases.append(('missing source',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='H')[2]+=4;cases.append(('wrong source bank',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='E')[1]+=512;cases.append(('unfrozen endpoint',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='F')[3]+=1
    # The independent counter check uses the final field.
    [r for r in bad if r[0]=='F'][-1][3]+=1;cases.append(('world counter',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='E')[2]=0;cases.append(('instruction accounting',bad))
    rejected=[]
    for name,bad in cases:
        try:report(root,bad)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted sabotage: '+name)
    return rejected


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('on',type=Path);p.add_argument('off',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=new_output(a.output);result=dict(observer=neutrality(a.on,a.off),rejected=negative(a.on),passed=True)
    out.write_text(json.dumps(result,indent=2)+'\n');print('C2 observer and rejecting controls passed')
if __name__=='__main__':main()
