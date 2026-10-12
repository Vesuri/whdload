#!/usr/bin/env python3
"""Revalidate available DMA/idle/callback evidence; not the full phase-4 gate."""
import argparse
import json
from pathlib import Path
from cd32_runtime import ROOT
from matrix_dma_check import check as dma_check
from matrix_idle_check import check as idle_check
from matrix_irq_check import check as irq_check
from matrix_irq_beam_check import check as beam_check
from matrix_irq_trace_check import compare_control
from matrix_raw_check import check as raw_check, compare as neutral_check

ROLES=('dma_bare','idle','dma','irq_bare','irq','beam')


def validate(cell):
    paths={key:(ROOT/cell[key]).resolve() for key in ROLES}
    missing=[key for key,path in paths.items() if not (path/'result.json').exists()]
    if missing:return dict(name=cell['name'],status='pending',missing=missing)
    metas={key:json.loads((path/'result.json').read_text()) for key,path in paths.items()}
    reference=json.loads((ROOT/cell['reference']).read_text())
    for key,meta in metas.items():
        if not meta.get('complete'):raise ValueError('incomplete run: '+key)
        for field in ('machine','options','audit_cacr','hunks','slave','slave_sha256'):
            if meta[field]!=reference[field]:raise ValueError('reference mismatch: '+key+'/'+field)
        if key!='beam' and meta.get('diagnostic_stops'):raise ValueError('diagnostic baseline arm: '+key)
    for group,roles in (('dma_audit',('dma_bare','idle','dma')),('irq_audit',('irq_bare','irq')),('beam_audit',('beam',))):
        audit=json.loads((ROOT/cell[group]).read_text())
        for role in roles:
            meta=metas[role]
            if not audit.get('complete'):raise ValueError('incomplete audit: '+group)
            for field in ('machine','options','emulator_sha256'):
                if audit[field]!=meta[field]:raise ValueError('audit mismatch: '+role+'/'+field)
            if audit['cacr']!=meta['audit_cacr'] or bool(audit.get('nommu_core'))!=bool(meta.get('nommu_core')):
                raise ValueError('audit cache/core mismatch: '+role)
    evidence={}
    for key in ROLES:
        if key!='beam':evidence[key+'_raw']=raw_check(paths[key])
    evidence['idle']=idle_check(paths['idle'])
    evidence['idle_neutrality']=neutral_check(paths['dma_bare'],paths['idle'])
    if not evidence['idle_neutrality']['idle_neutrality_pass']:raise ValueError('not an isolated idle control')
    evidence['dma']=dma_check(paths['dma'])
    evidence['dma_neutrality']=neutral_check(paths['idle'],paths['dma'])
    if not evidence['dma_neutrality']['dma_neutrality_pass']:raise ValueError('not an isolated DMA control')
    evidence['irq']=irq_check(paths['irq'])
    evidence['irq_neutrality']=neutral_check(paths['irq_bare'],paths['irq'])
    if not evidence['irq_neutrality']['irq_scope_neutrality_pass']:raise ValueError('not an isolated IRQ control')
    evidence['beam']=beam_check(paths['beam'])
    evidence['beam_control']=compare_control(paths['beam'],paths['irq'])
    # Distinct instrument builds must still have exactly the same baseline events.
    if (paths['dma_bare']/'matrix-events.txt').read_bytes()!=(paths['irq_bare']/'matrix-events.txt').read_bytes():
        raise ValueError('DMA and callback baselines differ')
    return dict(name=cell['name'],status='validated',evidence=evidence,
                scope='DMA slots, stopped-CPU idle and three callback elapsed scopes only; not complete CPU/interrupt accounting.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('fresh tmp output required')
    cells=json.loads(args.manifest.read_text())
    names=[cell['name'] for cell in cells]
    if len(set(names))!=len(names) or any(not n or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in n) for n in names):
        raise ValueError('unique simple cell names required')
    out.mkdir();(out/'manifest.json').write_text(json.dumps(cells,indent=2)+'\n')
    summary=[]
    for cell in cells:
        try:result=validate(cell)
        except (ValueError,KeyError,FileNotFoundError) as error:
            result=dict(name=cell['name'],status='invalid',error=str(error))
        (out/(cell['name']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        summary.append({key:value for key,value in result.items() if key!='evidence'})
        print(cell['name']+': '+result['status'],flush=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if any(row['status']=='invalid' for row in summary):raise SystemExit(1)


if __name__=='__main__':main()
