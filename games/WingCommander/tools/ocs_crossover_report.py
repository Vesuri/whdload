#!/usr/bin/env python3
"""Strict C2 field/DMA/pixel report. Model measurements, never hardware claims."""
import argparse
from collections import defaultdict
import json
import hashlib
from pathlib import Path
from ocs_baseline_report import parse, distribution, require
from ocs_reconstruct import new_output


def report(root, rows=None):
    meta=json.loads((root/'result.json').read_text())
    rows=parse(root/(meta['scene']+'-events.txt')) if rows is None else rows
    groups=defaultdict(list)
    for r in rows: groups[r[0]].append(r)
    require(len(groups['B'])==len(groups['E'])==1,'window edges')
    begin,end=groups['B'][0],groups['E'][0]
    fields=groups['F']; require([r[2] for r in fields]==list(range(1,251)),'incomplete fields')
    require(fields[-1][1]==end[1],'unfrozen endpoint')
    require(begin[2:4]==[28375160,512],'PAL clock')
    steps=[b-a for a,b in zip([begin[1]]+[r[1] for r in fields[:-1]],[r[1] for r in fields])]
    require(set(steps)<={227*312*512,227*313*512},'field calibration')
    hz=28375160/8*512; ms=lambda x:x/hz*1000
    seconds=(end[1]-begin[1])/hz
    require(.98<=sum(end[2:])/(end[1]-begin[1])<=1,'instruction accounting')
    dma=groups['D']
    require(len(dma)==250 and [r[2] for r in dma]==list(range(250)),'missing/mixed display fields')
    flips=[b for a,b in zip(dma,dma[1:]) if a[3]!=b[3]]
    p=defaultdict(list)
    for r in groups['P']: p[r[2]].append(r)
    require(len(flips)>3 and len(p[0x2dc])>3,'insufficient world/display coverage')
    require(len(p[0x2dc])==((fields[-1][3]-begin[5])&65535),'world counter mismatch')
    used=set(); delays=[]
    for d in flips:
        matches=[(i,r) for i,r in enumerate(p[0x33aa8]) if i not in used and r[1]<d[1] and r[5]==d[3]]
        require(len(matches)==1,'publication/DMA mismatch')
        i,r=matches[0];used.add(i);delays.append(ms(d[1]-r[1]))
    left=[r for i,r in enumerate(p[0x33aa8]) if i not in used]
    require(len(left)<=1 and all(r[1]>=fields[-2][1] for r in left),'unseen publication')
    # COP2LC publication during the final field may latch only after the cap,
    # even when its timestamp precedes that field's first old-buffer DMA.
    require(len(groups['X'])>=3 and all(r[2]==0 for r in groups['X']),'live converter pixel mismatch')
    conversions=[]; services=[]; queue_residual=[]; field_waits=[]
    for a in p[0x32626]:
        later=[r[1] for r in p[0x32626] if r[1]>a[1]]
        limit=later[0] if later else end[1]
        done=[r for r in p[0x32e06] if a[1]<=r[1]<limit]
        require(len(done)<=1,'duplicate completion')
        if done:
            total=done[0][1]-a[1];conversions.append(ms(total))
            if meta['arm']=='native':
                def stamp(off):
                    hits=[r[1] for r in p[off] if a[1]<=r[1]<=done[0][1]]
                    require(len(hits)==1,'native stage coverage')
                    return hits[0]
                service=sum(stamp(b)-stamp(c) for c,b in ((0x329e4,0x32a0a),(0x32a26,0x32a4a),(0x32dba,0x32e02)))
                require(0<service<=total,'native queue accounting')
                services.append(ms(service));queue_residual.append(ms(total-service))
                field_waits.append(ms(stamp(0x32944)-stamp(0x3293a)))
    scopes=defaultdict(list)
    for r in groups['R']:
        require(begin[1]<=r[3]<=r[1]<=end[1],'scope outside window')
        scopes[r[2]].append(ms(r[1]-r[3]))
    draw=[]
    for r in p[0x3260a]:
        starts=[s[1] for s in groups['S'] if s[2]==0x2e6 and s[1]<r[1]]
        if starts:draw.append(ms(r[1]-starts[-1]))
    native=meta['arm']=='native'
    require(bool(p[0x329de])==native,'selected backend was not executed')
    require(begin[4]==(256 if meta['cpu']=='68000' else 128),'CPU clock unit')
    require(len(groups['H'])==len(p[0x32626]),'source coverage')
    source=meta['installation']['source']
    require(all(r[2]==source and r[3]==meta['installation']['width']*meta['installation']['height'] for r in groups['H']),'source storage changed')
    end_memory=(root/'end-fast.bin').read_bytes()
    h0=meta['hunks'][0]-meta.get('memory_base',0x200000)
    if not native:
        import struct
        require(end_memory[h0+0x3291e:h0+0x32924]==struct.pack('>HI',0x4ef9,meta['installation']['code']),'CPU hook not retained')
    i=meta['installation'];base=meta.get('memory_base',0x200000)
    code=i['code']-base;source_offset=code+0x2000
    adapter=(root/'adapter.bin').read_bytes()
    require(end_memory[code:code+len(adapter)]==adapter,'adapter code changed')
    require(end_memory[code+len(adapter):source_offset]==bytes(0x2000-len(adapter)),'code/source guard changed')
    require(end_memory[source_offset+64000:code+i['tail_bytes']]==bytes(i['tail_bytes']-0x2000-64000),'source trailing guard changed')
    if meta['arm'].startswith('fast'):
        before=(root/'install-chip.bin').read_bytes();after=(root/'end-chip.bin').read_bytes()
        old=i['original_source'];size=i['width']*i['height']
        require(before[old:old+size]==after[old:old+size],'stale writer to old Chip source')
    opts=meta['effective']
    slow=meta.get('memory')=='slow'
    for k,v in dict(cpu_model=meta['cpu'],chipset='ocs',chipmem_size='1',fastmem_size='0' if slow else '4',bogomem_size='7' if slow else '0',cpu_frequency='0',cpu_cycle_exact='true',blitter_cycle_exact='true').items():
        require(opts.get(k)==v,'effective machine: '+k)
    require(len(groups['T'])==1 and sum(groups['T'][0][1:])*512<end[1]-begin[1],'DMA wait accounting')
    return dict(arm=meta['arm'],cpu=meta['cpu'],scene=meta['scene'],seconds=seconds,
        clock_unit=begin[4],displayed=len(flips),fps=len(flips)/seconds,world=len(p[0x2dc]),
        frame_ms=distribution([ms(b[1]-a[1]) for a,b in zip(flips,flips[1:])]),
        conversion_ms=distribution(conversions),
        native_scheduling=dict(service_ms=distribution(services),queue_residual_ms=distribution(queue_residual),field_wait_ms=distribution(field_waits)) if services else None,
        world_ms=distribution(scopes[0x2be]),
        drawing_ms=distribution(draw),publication_delay_ms=distribution(delays),
        cpu_poll_total_ms=dict(field=ms(end[3]),blitter=ms(end[4])),
        dma_contention_ms=[ms(x*512) for x in groups['T'][0][1:]] if groups['T'] else None,
        instruction_accounting_fraction=sum(end[2:])/(end[1]-begin[1]),
        pixel_checks=len(groups['X']),source_hashes=[r[4] for r in groups['H']],
        fingerprints={k:meta[k] for k in ('slave_sha256','fsuae_sha256')},passed=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--matched',action='store_true')
    a=p.parse_args(); out=new_output(a.output)
    checked=[report(x) for x in a.runs]
    results=matched(a.runs) if a.matched else checked
    out.write_text(json.dumps(results,indent=2)+'\n')
    if a.matched: print(results['cpu'],results['memory'],results['scene'],results['source_prefix_images'],'identical source images')
    else:
        for r in results:print(r['cpu'],r['scene'],r['arm'],round(r['fps'],3),round(r['conversion_ms']['mean'],3),r['pixel_checks'])


def matched(roots):
    """Compare common byte-exact source prefix and unchanged starting game state."""
    meta=[json.loads((r/'result.json').read_text()) for r in roots]
    for key in ('cpu','scene','memory','memory_base','memory_length','slave_sha256','fsuae_sha256','hunks','a4'):
        require(all(m[key]==meta[0][key] for m in meta),'unmatched '+key)
    require(meta[0]['arm']=='native','first arm must be native')
    snapshots=[(r/'install-fast.bin').read_bytes() for r in roots]
    from ocs_runtime import SIZES
    for base,size in zip(meta[0]['hunks'],SIZES):
        offset=base-meta[0]['memory_base']
        require(all(s[offset:offset+size]==snapshots[0][offset:offset+size] for s in snapshots),'starting game state differs')
    chip=[(r/'install-chip.bin').read_bytes() for r in roots]
    require(all(x==chip[0] for x in chip),'starting Chip/DMA state differs')
    streams=[];records=[];stream_hashes=[]
    for root,m in zip(roots,meta):
        records.append(parse(root/(m['scene']+'-events.txt')))
        hs=[r for r in records[-1] if r[0]=='H']
        size=m['installation']['width']*m['installation']['height']
        raw=(root/(m['scene']+'-events.txt.sources')).read_bytes()
        require(len(raw)==size*len(hs),'source stream coverage')
        streams.append([raw[i:i+size] for i in range(0,len(raw),size)])
        for frame,event in zip(streams[-1],hs):
            value=2166136261
            for byte in frame:value=((value^byte)*16777619)&0xffffffff
            require(value==event[4],'source stream/event disagreement')
        stream_hashes.append(hashlib.sha256(raw).hexdigest())
    prefix=0
    for frames in zip(*streams):
        if any(x!=frames[0] for x in frames):break
        prefix+=1
    require(prefix>=4,'too few identical source images')
    samples=[]
    for rows in records:
        hs=[r for r in rows if r[0]=='H']; ends=[r for r in rows if r[0]=='P' and r[2]==0x32e06]
        pubs=[r for r in rows if r[0]=='P' and r[2]==0x33aa8]; dma=[r for r in rows if r[0]=='D']
        pairs=[]
        for i,h in enumerate(hs[:prefix]):
            limit=hs[i+1][1] if i+1<len(hs) else next(r[1] for r in rows if r[0]=='E')
            completed=[r for r in ends if h[1]<=r[1]<limit]
            if not completed:break
            require(len(completed)==1,'completion ambiguity')
            done=completed[0][1]
            pub=next((r for r in pubs if r[1]>=done),None)
            if not pub:break
            display=next((r for r in dma if r[1]>pub[1] and r[3]==pub[5]),None)
            if not display:break
            # Inclusive overlap with native world work; CPU conversion cannot
            # overlap the next main-task call. IRQ work stays within phase cost.
            overlap=sum(max(0,min(done,r[1])-max(h[1],r[3])) for r in rows if r[0]=='R' and r[2]==0x2be)
            draw_overlap=0
            starts=[r[1] for r in rows if r[0]=='S' and r[2]==0x2e6]
            for finish in (r[1] for r in rows if r[0]=='P' and r[2]==0x3260a):
                previous=[t for t in starts if t<finish]
                if previous:draw_overlap+=max(0,min(done,finish)-max(h[1],previous[-1]))
            worlds=[r for r in rows if r[0]=='R' and r[2]==0x2be and r[1]<h[1]]
            finishes=[r[1] for r in rows if r[0]=='P' and r[2]==0x3260a and r[1]<=h[1]]
            require(worlds and finishes,'missing matched drawing/world scope')
            starts_before=[t for t in starts if t<finishes[-1]]
            require(starts_before,'missing matched draw entry')
            pairs.append((display[1],done-h[1],overlap,draw_overlap,
                          worlds[-1][1]-worlds[-1][3],finishes[-1]-starts_before[-1]))
        samples.append(pairs)
    n=min(map(len,samples));require(n>=4,'too few completed matched images')
    hz=28375160/8*512;ms=lambda x:x/hz*1000
    result=[]
    for m,values in zip(meta,samples):
        values=values[:n]
        intervals=[ms(b[0]-a[0]) for a,b in zip(values,values[1:])]
        result.append(dict(arm=m['arm'],images=n,intervals=n-1,
                           fps=(n-1)*hz/(values[-1][0]-values[0][0]),
                           frame_ms=distribution(intervals),conversion_ms=distribution([ms(x[1]) for x in values]),
                           world_conversion_overlap_ms=distribution([ms(x[2]) for x in values]),
                           drawing_conversion_overlap_ms=distribution([ms(x[3]) for x in values]),
                           world_ms=distribution([ms(x[4]) for x in values]),
                           drawing_ms=distribution([ms(x[5]) for x in values])))
    return dict(cpu=meta[0]['cpu'],memory=meta[0]['memory'],scene=meta[0]['scene'],
                initial_game_hunks_and_chip_exact=True,source_prefix_images=prefix,
                source_stream_sha256=stream_hashes,arms=result)

if __name__=='__main__':main()
