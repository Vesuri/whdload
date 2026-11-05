#!/usr/bin/env python3
"""P13A4 native OCS baseline: emulated-time measurements and rejecting controls."""
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import statistics
from PIL import Image
from ocs_boot_compare import equal_bytes, memory_contract
from ocs_runtime import SIZES


def require(ok, message):
    if not ok:
        raise ValueError(message)


def distribution(values):
    require(bool(values), 'empty measurement')
    values = sorted(values)
    def pct(q):
        # Linear percentiles; retain n so short-window tails are not oversold.
        x = (len(values)-1)*q
        lo = int(x)
        return values[lo]+(values[min(lo+1, len(values)-1)]-values[lo])*(x-lo)
    return dict(n=len(values), mean=statistics.mean(values), p50=pct(.5),
                p95=pct(.95), p99=pct(.99), maximum=values[-1])


def parse(path):
    rows=[]
    for line in path.read_text().splitlines():
        parts=line.split(); kind=parts[0]
        hex_columns={'P':{2,3,4}, 'S':{2}, 'R':{2,4}, 'D':{4}}.get(kind,set())
        rows.append([kind]+[int(value,16 if n in hex_columns else 10)
                            for n,value in enumerate(parts[1:],1)])
    return rows


def measure(rows):
    groups=defaultdict(list)
    for row in rows: groups[row[0]].append(row)
    require(len(groups['B'])==len(groups['E'])==1,'missing/duplicate window edges')
    begin,end=groups['B'][0],groups['E'][0]
    start,stop=begin[1],end[1]
    fields=groups['F']
    require([f[2] for f in fields]==list(range(1,251)), 'incomplete 250-field window')
    require(fields[-1][1]==stop,'live denominator after frozen endpoint')
    ticks=[b-a for a,b in zip([start]+[f[1] for f in fields[:-1]],[f[1] for f in fields])]
    require(begin[3]==512 and begin[4]==256,'unexpected colour/CPU cycle units')
    require(set(ticks)<={227*312*512,227*313*512},'field-clock calibration failed')
    require(begin[2]==28375160, 'unexpected PAL master clock')
    hz=begin[2]/8*begin[3]
    ms=lambda t:t/hz*1000
    seconds=(stop-start)/hz
    accounted=sum(end[2:])
    require(0 <= accounted <= stop-start, 'instruction accounting exceeds elapsed window')
    require(accounted/(stop-start) > .98, 'incomplete instruction accounting')
    p=groups['P']
    bypc=defaultdict(list)
    for row in p: bypc[row[2]].append(row)
    updates=len(bypc[0x2dc])
    require(updates==((fields[-1][3]-begin[5])&65535),'world recorder/native counter disagreement')
    require(updates>0 and len(bypc[0x32626])>=4,'no meaningful motion/conversion coverage')
    # One first plane-0 DMA observation per field. Multiple buffer ranges in a
    # field fail, rather than becoming extra "frames" or silently being ignored.
    dma=groups['D']
    require(len(dma)==250 and [d[2] for d in dma]==list(range(250)),
            'missing display field or mixed buffers in a field')
    flips=[b for a,b in zip(dma,dma[1:]) if a[3]!=b[3]]
    pubs=bypc[0x33aa8]
    require(len(pubs)>=4,'no publication coverage')
    # Every interior DMA change needs exactly one native publication, in order;
    # retain the one possible pending picture at either window boundary.
    delays=[]; used=set()
    for d in flips:
        candidates=[(i,r) for i,r in enumerate(pubs) if i not in used and r[1]<d[1] and r[5]==d[3]]
        require(len(candidates)==1,'publication/DMA counter disagreement')
        i,r=candidates[0]; used.add(i); delays.append(ms(d[1]-r[1]))
    leftovers=[r for i,r in enumerate(pubs) if i not in used]
    require(len(leftovers)<=1 and all(r[1]>dma[-1][1] for r in leftovers),'unseen interior publication')
    require(len(flips)>=4,'too few displayed intervals')
    intervals=[ms(b[1]-a[1]) for a,b in zip(flips,flips[1:])]
    scopes=defaultdict(list)
    for r in groups['R']:
        require(start<=r[3]<=r[1]<=stop,'scope outside frozen window')
        scopes[r[2]].append(ms(r[1]-r[3]))
    # Complete conversions only; partial boundary calls are retained in raw data.
    conversions=[]
    for first in bypc[0x32626]:
        following=[r for r in bypc[0x32626] if r[1]>first[1]]
        limit=following[0][1] if following else stop
        ev=[r for r in p if first[1]<=r[1]<limit]
        eventmap=defaultdict(list)
        for r in ev:eventmap[r[2]].append(r)
        if not eventmap[0x32e02]:continue
        def one(off):
            require(len(eventmap[off])==1, f'conversion stage coverage {off:x}')
            return eventmap[off][0][1]
        stagepairs=[(0x329e4,0x32a0a),(0x32a26,0x32a4a),(0x32dba,0x32e02)]
        services=[one(b)-one(a) for a,b in stagepairs]
        require(all(t>0 for t in services),'negative service time')
        submits=eventmap[0x329de]
        require(len(submits)==3,'not three QBlit submissions')
        require(submits[0][1] <= one(0x329e4) < one(0x32a0a) <= submits[1][1] <=
                one(0x32a26) < one(0x32a4a) <= submits[2][1] <= one(0x32dba) < one(0x32e02),
                'conversion service/queue ordering differs')
        total=one(0x32e02)-submits[0][1]
        residual=total-sum(services)
        require(residual>=0,'service/wait accounting exceeds conversion')
        fieldwait=one(0x32944)-one(0x3293a)
        # Field pacing overlaps stage 1: never add this independently to service.
        conversions.append(dict(total=ms(total),service=ms(sum(services)),
            queue_and_scheduling=ms(residual),field_wait=ms(fieldwait),
            stage1=ms(services[0]),stage2=ms(services[1]),stage3=ms(services[2])))
    require(len(conversions)>=3,'too few complete conversions')
    drawing=[]
    entries=[r[1] for r in groups['S'] if r[2]==0x2e6]
    for finish in bypc[0x3260a]:
        before=[t for t in entries if t<finish[1]]
        if before:drawing.append(ms(finish[1]-before[-1]))
    census=[r for r in groups['C'] if r[3]]
    require(len(census)>=3,'no comparable source frames')
    require(all(0<=r[4]<=r[2] and 0<=r[5]<=r[2]//32 for r in census),'invalid source census')
    memory=groups['M']
    require(all(0<r[2]<524288 and 0<r[3]<4194304 for r in memory),'invalid memory census')
    return dict(seconds=seconds,fields=250,field_ticks=sorted(set(ticks)),
        field_rate_hz=250/seconds,world_updates=updates,world_updates_per_second=updates/seconds,
        published_pictures=len(pubs),displayed_changes=len(flips),boundary_pending=len(leftovers),
        displayed_pictures_per_second=len(flips)/seconds,display_interval_ms=distribution(intervals),
        publication_to_first_dma_ms=distribution(delays),
        world_scope_ms=distribution(scopes[0x2be]), drawing_to_submission_ms=distribution(drawing),
        conversion_ms={key:distribution([c[key] for c in conversions]) for key in conversions[0]},
        flag_wait_scope_ms=distribution(scopes[0x3407e]),
        cpu_poll_ms=dict(field_spin=ms(end[3]),blitter_poll=ms(end[4])),
        instruction_accounting=dict(recorded_ms=ms(accounted), elapsed_ms=ms(stop-start),
            fraction=accounted/(stop-start), outside_instructions_ms=ms(stop-start-accounted)),
        source_changed_fraction=distribution([r[4]/r[2] for r in census]),
        source_changed_32byte_block_fraction=distribution([r[5]/(r[2]//32) for r in census]),
        memory_sampled_used_high_water=dict(chip=524288-min(r[2] for r in memory),
            fast=4194304-min(r[3] for r in memory),samples=len(memory)),
        landmarks={f'{pc:x}':len(events) for pc,events in bypc.items()},
        completed_calls={f'{pc:x}':len(values) for pc,values in scopes.items()})



def memory_pools(root, label):
    chip=(root/(label+'-chip.bin')).read_bytes()
    fast=(root/(label+'-fast.bin')).read_bytes()
    def read(address,n=4):
        data=chip[address:address+n] if address<0x80000 else fast[address-0x200000:address-0x200000+n]
        require(len(data)==n,'memory header outside snapshot')
        return int.from_bytes(data,'big')
    header=read(read(4)+322); pools={}
    for _ in range(16):
        if not read(header):return pools
        attrs=read(header+14,2); kind='chip' if attrs&2 else 'fast' if attrs&4 else None
        require(kind and kind not in pools,'unexpected memory pool')
        pools[kind]=read(header+24)-read(header+20)
        header=read(header)
    raise ValueError('unterminated memory list')


def negative_controls(rows):
    mutations=[]
    bad=copy.deepcopy(rows); next(r for r in bad if r[0]=='B')[4]=231
    mutations.append(('wrong CPU clock',bad))
    bad=copy.deepcopy(rows); next(r for r in reversed(bad) if r[0]=='F')[3]+=1
    mutations.append(('world counter mismatch',bad))
    bad=copy.deepcopy(rows); bad.remove(next(r for r in bad if r[0]=='D'))
    mutations.append(('missing DMA field',bad))
    bad=copy.deepcopy(rows); pubs=[r for r in bad if r[0]=='P' and r[2]==0x33aa8];bad.remove(pubs[2])
    mutations.append(('missing publication',bad))
    bad=copy.deepcopy(rows); bad.remove(next(r for r in bad if r[0]=='P' and r[2]==0x32a4a))
    mutations.append(('missing conversion stage',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='F')[1]+=512
    mutations.append(('bad field duration',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='E')[1]+=512
    mutations.append(('unfrozen denominator',bad))
    bad=copy.deepcopy(rows);c=next(r for r in bad if r[0]=='C' and r[3]);c[4]=c[2]+1
    mutations.append(('invalid change census',bad))
    bad=copy.deepcopy(rows);next(r for r in bad if r[0]=='E')[2]=0
    mutations.append(('missing instruction accounting',bad))
    for label,bad in mutations:
        try:measure(bad)
        except ValueError:pass
        else:raise AssertionError('negative control accepted: '+label)
    for bad in (b'\x00\x02', b'\x00'):
        try:equal_bytes(b'\x00\x01',bad,2,'state/pixel sabotage')
        except ValueError:pass
        else:raise AssertionError('strict comparison accepted corruption')
    return [label for label,_ in mutations]+['changed state/pixel byte','truncated state/pixel bytes']


def neutrality(on,off):
    a,b=[json.loads((root/'result.json').read_text()) for root in (on,off)]
    require(a['baseline']=='on' and b['baseline']=='off','wrong observer control pair')
    for key in ('machine','warp','variant','fsuae_sha256','hunks','a4','actions','checkpoints',
                'whd_args','effective','slave_sha256','fields_per_window'):
        require(a[key]==b[key],'different run contract: '+key)
    require(a['machine']=='a500-ocs-512k-chip-4m-fast' and not a['warp'] and not a['whd_args'],
            'not the nominated machine')
    require(a['slave_sha256']=='eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913',
            'baseline is not the pinned original OCS slave')
    require(a['checkpoints']==['origin','title','credits','menu','simulator','name','asteroids','fire'],
            'incomplete control checkpoints')
    for label in a['checkpoints']:
        for n,size in enumerate(SIZES):
            equal_bytes(*[(p/f'{label}-h{n}.bin').read_bytes() for p in (on,off)],size,label+f' h{n}')
        equal_bytes(*[(p/f'{label}-chip.bin').read_bytes() for p in (on,off)],524288,label+' Chip')
        images=[Image.open(p/(label+'.png')).convert('RGB') for p in (on,off)]
        require(images[0].size==images[1].size==(754,576),'picture dimensions differ')
        equal_bytes(*[im.tobytes() for im in images],images[0].width*images[0].height*3,label+' pixels')
        require(memory_contract(on,label)==memory_contract(off,label),'memory contract differs')
    for label in ('asteroids','fire'):
        edges=[[r for r in parse(root/(label+'-events.txt')) if r[0] in ('B','F','M')]
               for root in (on,off)]
        # On additionally samples allocator returns: compare exact field edges.
        require([[r for r in e if r[0]!='M'] for e in edges][0]==
                [[r for r in e if r[0]!='M'] for e in edges][1],'observer changed window clocks/counters')
    return dict(checkpoints=len(a['checkpoints']),state_and_pixels_exact=True,
                slave_sha256=a['slave_sha256'],emulator_sha256=a['fsuae_sha256'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('on',type=Path);p.add_argument('off',type=Path)
    a=p.parse_args()
    result=dict(observer_control=neutrality(a.on,a.off),windows={})
    for label in ('asteroids','fire'):
        rows=parse(a.on/(label+'-events.txt'))
        result['windows'][label]=measure(rows)
        pools=memory_pools(a.on,label)
        before='credits' if label=='asteroids' else 'simulator'
        require(pools==memory_pools(a.on,before),'native memory pools changed')
        memory=result['windows'][label].pop('memory_sampled_used_high_water')
        result['windows'][label]['memory']={
            'sample_count':memory['samples'],
            'physical_unavailable_high_water':{k:memory[k] for k in pools},
            'native_pool_capacity':pools,
            'native_pool_used_high_water':{k:memory[k]-({'chip':524288,'fast':4194304}[k]-pools[k]) for k in pools},
            'outside_native_pool':{k:{'chip':524288,'fast':4194304}[k]-pools[k] for k in pools}}
        result['windows'][label]['negative_controls']=negative_controls(rows)
    require(result['windows']['asteroids']['landmarks'].get('9618',0)>0,'no asteroid generation')
    require(result['windows']['fire']['completed_calls'].get('c748',0)>0,'no firing coverage')
    result['passed']=True
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
