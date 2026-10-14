#!/usr/bin/env python3
"""Check C4 installed ownership and pixels, and report observed memory usage.
Snapshots establish sampled usage, not a boot-wide high-water mark. No speed
claim follows from this correctness run, which may include debugger stops.
"""
import argparse
import json
import hashlib
import struct
import _amigaxdev
from amigaxdev import barto
from pathlib import Path
from collections import defaultdict
from ocs_baseline_report import parse
from ocs_reconstruct import new_output, require
from ocs_memory_build import HOOKS, NATIVE


def report(root, build):
    m=json.loads((root/'result.json').read_text())
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    require(hashlib.sha256((build/'WingCommander.Slave').read_bytes()).hexdigest()==b['sha256'],'changed candidate artifact')
    require(m['slave_sha256']==b['sha256'],'wrong candidate run')
    require(set(('origin','title','credits','menu','simulator','name'))<=set(m['checkpoints']),'missing transition')
    history=b.get('history_bytes',0)
    if history:
        require(history==128000,'unknown history extent')
        first=m['slave']+sy['ocs_changed_history']
        require(0x200000<=first and first+history<=m['slave']+b['bytes']-36<=0xa00000,'history outside owned Fast hunk')
    samples=[];teardown=None;expected_backend=0 if b['backend']!='cpu' else 1 if m['effective']['cpu_model']=='68000' else 2
    for label in m['checkpoints']:
        chip=(root/(label+'-chip.bin')).read_bytes();fast=(root/(label+'-fast.bin')).read_bytes()
        def read(a,n=4):
            if 0<=a<=len(chip)-n:return chip[a:a+n]
            require(0x200000<=a<=0x200000+len(fast)-n,'pointer outside RAM')
            return fast[a-0x200000:a-0x200000+n]
        def integer(a,n=4):return int.from_bytes(read(a,n),'big')
        h0=m['hunks'][0];slave=m['slave'];a4=m['a4']
        requested=integer(slave+sy['ocs_requested_backend']);selected=integer(slave+sy['ocs_source_backend'])
        if label=='teardown':
            require(selected==0 and integer(a4+0x10e6)==0 and integer(a4+0x10ea)==0,'source survives exit')
            require(integer(h0+0x324a8)==integer(h0+0x324b0)==0,'stale converter owner')
            require(integer(h0+0x324b8)==integer(h0+0x324bc)==integer(h0+0x331c0)==0,'display survives exit')
            count=integer(a4-0x844,2)
            owned=[integer(a4+0x4a2+4*i) for i in range(count)]
            require(samples[0]['source'] not in owned,'source remains registered after exit')
            teardown=dict(source_and_display_released=True,registry_allocations=count)
            continue
        require(requested==expected_backend and selected==requested,'unexpected fallback or backend')
        for off,name,op in b.get('hooks',HOOKS):
            require(integer(h0+off,2)==op and integer(h0+off+2)==slave+sy[name],'missing installed hook')
        surface=a4+0x10e2
        source=integer(surface+4);size=integer(surface+12);rows=integer(surface+8)
        require(source==integer(h0+0x324b0) and size==64000,'main source owner differs')
        require(bool(selected)==(source>=0x200000),'wrong source bank')
        require(source+size<=(0x200000+len(fast) if selected else len(chip)),'source extent')
        count=integer(a4-0x844,2);require(0<count<=120,'native registry count')
        registry={integer(a4+0x4a2+4*i):integer(a4+0x682+4*i) for i in range(count)}
        require(len(registry)==count and registry.get(source)==size and registry.get(rows)==800,'source registry ownership')
        state=h0+0x331b8
        region=integer(state);workspace=integer(state+4);p0=integer(state+8);p1=integer(state+12)
        allocation=registry.get(p0,0)
        require(allocation>0 and allocation%3==0,'combined allocation registry')
        capacity=allocation//3
        require(region<=capacity and workspace==p0+capacity and p1==p0+2*capacity,'combined Chip layout')
        require(p0+allocation<=len(chip),'plane/workspace ownership')
        for off in (0x324b8,0x324bc):
            require(registry.get(integer(h0+off))==668,'conversion descriptor owner')
        # Real OS memory headers, not allocator-label inference.
        header=integer(integer(4)+322);headers=[]
        for _ in range(16):
            following=integer(header)
            if not following:break
            attrs=integer(header+14,2);lo=integer(header+20);hi=integer(header+24);free=integer(header+28)
            require(lo<hi and free<=hi-lo,'invalid memory header')
            headers.append(dict(attributes=attrs,lower=lo,upper=hi,free=free));header=following
        else:raise ValueError('memory list did not terminate')
        free_chip=sum(x['free'] for x in headers if x['attributes']&2)
        free_fast=sum(x['free'] for x in headers if x['attributes']&4)
        samples.append(dict(label=label,source=source,source_bytes=size,planes_and_workspace=allocation,
                            row_bytes=800,descriptor_bytes=1336,registry_allocations=count,
                            registry_chip_bytes=sum(n for p,n in registry.items() if p<0x80000),
                            registry_fast_bytes=sum(n for p,n in registry.items() if p>=0x200000),
                            chip_used=len(chip)-free_chip,fast_used=len(fast)-free_fast,
                            headers=headers))
    if teardown is not None:
        name_code=(root/'name-h0.bin').read_bytes()
        display=int.from_bytes(name_code[0x331c0:0x331c4],'big')
        source=samples[0]['source']
        ranges=((display,display+samples[0]['planes_and_workspace']),(source,source+64000))
        # graphics.library may reuse the freed Chip source for the restored
        # OS View's Copper list. Prove that new owner; a range-only blacklist
        # incorrectly calls these legitimate Copper reads stale source DMA.
        tc=(root/'teardown-chip.bin').read_bytes();tf=(root/'teardown-fast.bin').read_bytes()
        def tr(a,n=4):
            if 0<=a<=len(tc)-n:return tc[a:a+n]
            require(0x200000<=a<=0x200000+len(tf)-n,'teardown OS pointer outside RAM')
            return tf[a-0x200000:a-0x200000+n]
        def ti(a,n=4):return int.from_bytes(tr(a,n),'big')
        gfx=int.from_bytes(name_code[0x33518:0x3351c],'big')
        lib=ti(ti(4)+378);found=False
        for _ in range(64):
            if not ti(lib):break
            if lib==gfx:found=True
            lib=ti(lib)
        else:raise ValueError('unterminated library list')
        require(found and tr(ti(gfx+10),17)==b'graphics.library\0','restored graphics owner absent')
        view=ti(gfx+34);cpr=ti(view+4);cop=ti(cpr+4);cop_size=4*ti(cpr+8,2)
        require(view!=m['hunks'][0]+0x33562 and cop==ti(gfx+50),'OS View/Copper owner mismatch')
        require(0<cop_size<=4096 and 0<cop<cop+cop_size<=len(tc),'OS Copper extent')
        require(b'\xff\xff\xff\xfe' in tr(cop,cop_size),'OS Copper list lacks end')
        header=ti(ti(4)+322)
        for _ in range(16):
            if not ti(header):break
            if ti(header+14,2)&2:
                chunk=ti(header+16)
                for _ in range(1024):
                    if not chunk:break
                    size=ti(chunk+4)
                    require(not max(cop,chunk)<min(cop+cop_size,chunk+size),'OS Copper list is free memory')
                    chunk=ti(chunk)
                else:raise ValueError('unterminated Chip free list')
            header=ti(header)
        counts={}
        for label in ('name','teardown'):
            t=barto.load(str(root/(label+'-screen.bin')))
            hits=total=reused=0
            require(len(t.fields)>=2,'missing complete DMA field')
            for field in t.fields[1:]:
                require(field.dma_size==58,'unknown DMA record ABI')
                for pos in range(0,len(field.dma),58):
                    kind=struct.unpack_from('<h',field.dma,pos+29)[0]
                    reg=struct.unpack_from('<H',field.dma,pos)[0]
                    if reg==0xffff or kind not in (3,4,5,6,7,8):continue
                    address=struct.unpack_from('<I',field.dma,pos+12)[0]
                    total+=1
                    if any(lo<=address<hi for lo,hi in ranges):
                        if label=='teardown' and kind==3 and cop<=address<cop+cop_size:reused+=1
                        else:hits+=1
            require(total>0,'DMA observer absent')
            counts[label]=dict(total=total,stale_source_or_planes=hits,restored_os_copper_reads=reused)
        require(counts['name']['stale_source_or_planes']>0,'missing live DMA positive control')
        require(counts['teardown']['stale_source_or_planes']==0,'DMA reads freed source or planes')
        teardown['dma']=counts
    pixels=0
    for scene in ('asteroids','fire'):
        groups=defaultdict(list)
        for r in parse(root/(scene+'-events.txt')):groups[r[0]].append(r)
        fields=m.get('fire_fields',250) if scene=='fire' else 250
        require([r[2] for r in groups['F']]==list(range(1,fields+1)),'missing window fields')
        require(len(groups['X'])>=3 and all(r[2]==0 for r in groups['X']),'pixel mismatch')
        require(len(groups['D'])==fields,'missing display fields')
        scene_code=(root/(scene+'-h0.bin')).read_bytes()
        plane=int.from_bytes(scene_code[0x331d2:0x331d4],'big')
        buffers=struct.unpack_from('>II',scene_code,0x331c0)
        require(all(d[3] in (0,1) and buffers[d[3]]<=d[4]<buffers[d[3]]+plane
                    for d in groups['D']),'display DMA outside owned plane')
        publications=[r for r in groups['P'] if r[2]==0x33aa8]
        require(publications and all(0<r[3]<0x80000 and r[3]%2==0 for r in publications),
                'published Copper list outside Chip RAM')
        native=[r for r in groups['P'] if r[2]==0x329de]
        require(bool(native)==(expected_backend==0),'obsolete QBlit consumer executed')
        require(len(groups['H'])>=3 and all(r[2]==samples[0]['source'] for r in groups['H']),'source changed inside window')
        pixels+=len(groups['X'])
    return dict(passed=True,backend=expected_backend,pixel_checks=pixels,samples=samples,teardown=teardown,
                slave_bytes=b['bytes'],added_slave_bytes=b['bytes']-5324,
                new_history_bytes=history,new_prediction_bytes=0,
                memory_scope='sampled native registry and total OS pools; not boot-wide peaks')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--build',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=report(Path(a.run),Path(a.build));out=new_output(a.output);out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['pixel_checks'],'pixel checks; ownership passed')

if __name__=='__main__':main()
