#!/usr/bin/env python3
"""Diagnostic scene accounting; this is not a validated phase 4 baseline."""
import argparse,collections,json,re
from pathlib import Path


def read_aprof(path):
    lines=path.read_text().splitlines()
    if not lines or lines[0]!='AITDPROF 1':raise ValueError('unsupported profile')
    header={};pcs=[];nodes=[]
    for line in lines[1:]:
        p=line.split()
        if p[0]=='P':pcs.append([int(p[1],16)]+[int(x) for x in p[2:]])
        elif p[0]=='N':nodes.append([int(p[1]),int(p[2]),int(p[3],16)]+[int(x) for x in p[4:]])
        else:header[p[0]]=int(p[1],16 if p[0]=='cacr' else 10)
    if header['units']<=0 or not pcs:raise ValueError('empty profile')
    body=sum(p[1] for p in pcs)
    accounted=body+header['gap']+header['high']
    # A stop can include a final outside-instruction gap. Never erase it.
    residual=header['units']-accounted
    if residual<0:raise ValueError('profile overcounts elapsed units')
    if [n[0] for n in nodes]!=list(range(len(nodes))):raise ValueError('broken context ids')
    inclusive=[n[4] for n in nodes]
    for n in reversed(nodes[1:]):
        if n[1]>=n[0]:raise ValueError('cyclic context tree')
        inclusive[n[1]]+=inclusive[n[0]]
    if sum(n[4] for n in nodes)!=accounted:raise ValueError('PC/context accounting differs')
    return header,pcs,nodes,inclusive,residual


def report(run):
    meta=json.loads((run/'result.json').read_text())
    if not meta['complete']:raise ValueError('incomplete capture')
    if not meta.get('profiles',True):raise ValueError('aggregate profiling was disabled for this control')
    cpu=dict(re.findall(r'(\w+)=(\w+)',meta['boot_cpu']))
    if meta['machine'] not in ('a1200-fast','a1200-030') or cpu.get('mmu')!='0':
        raise ValueError('instruction report requires a covered 020/030 NOMMU core')
    boundaries=[];publications=collections.Counter();changes=collections.defaultdict(list)
    for line in (run/'matrix-events.txt').read_text().splitlines():
        p=line.split();kind=p[0];i=int(p[1])
        if kind=='B':boundaries.append((i,int(p[2],16),int(p[3]),int(p[4]),int(p[5],16)))
        elif kind=='P':
            publications[i]+=1
            if int(p[4],16)!=meta['audit_cacr']:raise ValueError('publication cache audit mismatch')
        elif kind=='C':
            if int(p[8],16)!=meta['audit_cacr']:raise ValueError('c2p cache audit mismatch')
            sample=[int(x) for x in p[4:8]]
            size,compared,changed,blocks=sample
            if size not in (320*128,320*166,320*200) or compared not in (0,1):
                raise ValueError('invalid c2p geometry/comparison flag')
            if not 0<=changed<=size or not 0<=blocks<=size//32 or not blocks<=changed<=blocks*32:
                raise ValueError('invalid c2p change census')
            if not compared and (changed or blocks):raise ValueError('unpaired frame has changes')
            changes[i].append(sample)
        else:raise ValueError('unknown census record')
    if [b[0] for b in boundaries]!=list(range(35)):raise ValueError('missing/reordered scene boundary')
    def symbol(pc):
        for i,(base,size) in enumerate(zip(meta['hunks'],(0x35ea4,0xfda0,4,0x1590))):
            if base<=pc<base+size:return f'h{i}:{pc-base:05x}'
        if meta['slave']<=pc<meta['slave']+0x1e0c:return f'S:{pc-meta["slave"]:04x}'
        if 0xf80000<=pc<0x1000000:return f'ROM:{pc-0xf80000:05x}'
        return f'other:{pc:08x}' # absolute runtime targets remain only in tmp/ reports
    scenes=[]
    for a,b in zip(boundaries,boundaries[1:]):
        i=a[0];h,pcs,nodes,inc,residual=read_aprof(run/f'scene-{i:02d}.aprof')
        if h['units']!=b[3]-a[3]:raise ValueError('scene clock/profile disagreement')
        expected_model=68020 if meta['machine']=='a1200-fast' else 68030
        expected_unit=128 if expected_model==68020 else int(cpu['unit'])
        if h['cpu_model']!=expected_model or h['cycleunit']!=expected_unit or h['CYCLE_UNIT']!=512 or h['colorclock_hz']!=3546895:
            raise ValueError('CPU/clock conversion differs from capture')
        if expected_model==68030 and not meta.get('nommu_core'):
            raise ValueError('explicit NOMMU 030 capture required')
        if h['cacr']!=meta['audit_cacr'] and i>0:raise ValueError('profile cache audit mismatch')
        if h['vsyncs']!=b[2]-a[2]:raise ValueError('scene field/profile disagreement')
        seconds=h['units']/h['CYCLE_UNIT']/h['colorclock_hz']
        groups=collections.defaultdict(lambda:[0,0,0])
        for n in nodes:
            key=(symbol(n[2]),n[3]);g=groups[key];g[0]+=n[4];g[1]+=inc[n[0]];g[2]+=n[5]
        routines=[dict(target=k[0],kind=k[1],self_units=v[0],inclusive_units=v[1],calls=v[2]) for k,v in groups.items()]
        routines.sort(key=lambda x:x['self_units'],reverse=True)
        samples=changes[i];pairs=[c for c in samples if c[1]]
        denominator=sum(c[0] for c in pairs)
        scenes.append(dict(scene=meta['names'][i],seconds=seconds,fields=b[2]-a[2],
            publications=publications[i],publication_hz=publications[i]/seconds,
            cacr=h['cacr'],profile=h,residual_units=residual,routines=routines,
            pc_self=[dict(target=symbol(p[0]),units=p[1],calls=p[2],chip_units=p[3],chip_accesses=p[4]) for p in sorted(pcs,key=lambda p:p[1],reverse=True)],
            c2p_calls=len(samples),compared_frames=len(pairs),compared_bytes=denominator,
            changed_bytes=sum(c[2] for c in pairs),changed_32byte_blocks=sum(c[3] for c in pairs),
            changed_fraction=sum(c[2] for c in pairs)/denominator if denominator else None))
    return dict(machine=meta['machine'],options=meta['options'],audit_cacr=meta['audit_cacr'],
                validated_baseline=False,
                limitations=['Inclusive/self routine contexts require unmatched-return investigation.',
                             'Repeat and observer-off comparisons require separate checks.',
                             'Whole-scene DMA, waits, interrupt cost and idle attribution remain incomplete.'],
                scenes=scenes)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    print(json.dumps(report(a.run),indent=2))

if __name__=='__main__':main()
