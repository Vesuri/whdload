#!/usr/bin/env python3
"""Reconcile queued OCS pictures, blanking-time publication and actual DMA pixels."""
import argparse
import copy
import json
from pathlib import Path
from ocs_baseline_report import parse
from ocs_memory_report import report as ownership
from ocs_reconstruct import new_output, require


def window(rows, fields):
    groups={k:[r for r in rows if r[0]==k] for k in ('F','D','Q','V','J','Y','X','P')}
    require([r[2] for r in groups['F']]==list(range(1,fields+1)),'missing window fields')
    require([r[2] for r in groups['D']]==list(range(fields)),'mixed or missing display buffers')
    require(len(groups['Y'])==fields,'missing DMA pixel observations')
    require(all(r[3]==0 for r in groups['Y']),'display DMA pixel mismatch')
    good=sum(r[2] for r in groups['Y']);unknown=sum(r[4] for r in groups['Y'])
    require(good>fields*1000,'insufficient actual DMA pixel coverage')
    require(len(groups['X'])>=3 and all(r[2]==0 for r in groups['X']),'completed pixel mismatch')
    require(len(groups['J'])==len(groups['V'])>=3,'missing Copper restart')
    for v,j in zip(groups['V'],groups['J']):
        require(v[1]<j[1] and v[3]==j[4] and 16<=v[4]<=32 and 16<=j[2]<=j[3]<=41,
                'publication outside OCS blank')
    pending=None;prepared=None;completed=False;matches=0
    for r in rows:
        if r[0]=='P' and r[2]==0x32e06:completed=True
        if r[0]=='Q':
            require(completed,'queued before conversion completion')
            require(pending is None,'overwrote pending picture')
            pending=r;completed=False
        if r[0]=='V':
            if pending is not None:
                require(r[3]==pending[3],'forecast/display field disagreement')
                matches+=1
        if r[0]=='P' and r[2]==0x33aa8:prepared=r
        if r[0]=='J':
            if pending is not None:
                require(prepared is not None and prepared[5]==pending[2],'published wrong pending owner')
            pending=None
        if r[0]=='P' and r[2] in (0x3342e,0x33350,0x333ba,0x334bc):
            require(pending is None,'reused or destroyed pending display')
    require(matches>=3,'no forecast reconciliation')
    pubs=[r for r in groups['P'] if r[2]==0x33aa8];used={i for i,r in enumerate(pubs) if r[1]<groups['D'][0][1]}
    flips=[b for a,b in zip(groups['D'],groups['D'][1:]) if a[3]!=b[3]]
    for d in flips:
        candidates=[(i,r) for i,r in enumerate(pubs) if i not in used and r[1]<d[1] and r[5]==d[3]]
        require(len(candidates)==1,'DMA differs from publication ledger')
        used.add(candidates[0][0])
    remaining=[r for i,r in enumerate(pubs) if i not in used]
    require(len(remaining)<=1 and all(r[1]<groups['D'][0][1] or r[1]>groups['D'][-1][1] for r in remaining),
            'unseen interior publication')
    return dict(fields=fields,completed_pixels=len(groups['X']),dma_words=good,
                unverified_words=unknown,forecasts=matches,display_changes=len(flips),
                restart_lines=sorted(set(r[3] for r in groups['J'])))


def report(root,build):
    own=ownership(root,build);m=json.loads((root/'result.json').read_text())
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    result={};starts=set()
    for label in m['checkpoints']:
        if label=='teardown':continue
        chip=(root/f'{label}-chip.bin').read_bytes();fast=(root/f'{label}-fast.bin').read_bytes()
        code=(root/f'{label}-h0.bin').read_bytes()
        def read(address,count):
            if 0<=address<=len(chip)-count:return chip[address:address+count]
            offset=address-0x200000
            require(0<=offset<=len(fast)-count,'Copper metadata outside RAM')
            return fast[offset:offset+count]
        def value(address):return int.from_bytes(read(address,4),'big')
        gfx=int.from_bytes(code[0x33518:0x3351c],'big');init=value(gfx+38)
        require(read(init+72,8)==bytes.fromhex('0c01fffe008a0000'),'unverified OS Copper jump')
        for offset in (0x3360c,0x33610):
            cpr=int.from_bytes(code[offset:offset+4],'big');pointer=value(cpr+4)
            require(0<pointer<pointer+224<=len(chip),'game Copper list outside Chip')
            data=read(pointer,224)
            require(data[136:140]==bytes.fromhex('01000200'),'planes enabled before safe blank')
            require(data[202:208]==bytes.fromhex('fffe01004200'),'unverified display enable')
            start=int.from_bytes(data[200:202],'big')>>8
            require(start>=72,'display begins before audited deadline');starts.add(start)
    for scene,fields in [('asteroids',250),('fire',m.get('fire_fields',250))]+[(f'view{x}',m.get('view_fields',100)) for x in (2,1,3,0) if f'view{x}' in m['checkpoints']]:
        result[scene]=window(parse(root/(scene+'-events.txt')),fields)
        if scene.startswith('view'):
            f=(root/(scene+'-fast.bin')).read_bytes();off=m['a4']-18318-0x200000
            requested=int(scene[-1]);observed=int.from_bytes(f[off:off+2],'big')
            require(any(x.get('checkpoint')==f'diagnostic native view {requested} active' for x in m['actions']),
                    'missing state-conditioned view entry')
            require(observed==requested or (requested==0 and observed==4),'unexpected view exit')
            result[scene].update(requested_view=requested,ending_view=observed)
            # The simulator may enter its native death camera during the final
            # front-view window; retain this transition rather than hiding it.
    # The IRQ request must be drained before display ownership can be released.
    if 'teardown' in m['checkpoints']:
        f=(root/'teardown-fast.bin').read_bytes()
        for symbol,size in [('ocs_pending',2),('ocs_front',4)]:
            off=m['slave']+sy[symbol]-0x200000
            require(int.from_bytes(f[off:off+size],'big')==0,'publication survives teardown')
    return dict(passed=True,windows=result,display_start_lines=sorted(starts),ownership=own)


def neutrality(on,off,build):
    a,b=[json.loads((r/'result.json').read_text()) for r in (on,off)]
    for key in ('hunks','slave','a4','slave_sha256','fsuae_sha256','effective','checkpoints'):
        require(a[key]==b[key],'observer contract differs: '+key)
    require(a['baseline']=='on' and b['baseline']=='off','wrong observer modes')
    size=json.loads((build/'build.json').read_text())['bytes']-36
    for label in a['checkpoints']:
        for n in range(4):
            require((on/f'{label}-h{n}.bin').read_bytes()==(off/f'{label}-h{n}.bin').read_bytes(),
                    'observer changed game state: '+label)
        require((on/f'{label}-chip.bin').read_bytes()==(off/f'{label}-chip.bin').read_bytes(),
                'observer changed Chip pixels: '+label)
        snapshots=[(r/f'{label}-fast.bin').read_bytes() for r in (on,off)]
        offset=a['slave']-0x200000
        require(snapshots[0][offset:offset+size]==snapshots[1][offset:offset+size],
                'observer changed owned publication state: '+label)
    for scene in ('asteroids','fire')+tuple(f'view{x}' for x in (2,1,3,0) if f'view{x}' in a['checkpoints']):
        edges=[[r for r in parse(p/f'{scene}-events.txt') if r[0] in ('B','F')] for p in (on,off)]
        require(edges[0]==edges[1],'observer changed emulated field timing')
    return dict(passed=True,checkpoints=len(a['checkpoints']),exact_game_chip_and_owned_state=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--build',required=True,type=Path);p.add_argument('--output',required=True);p.add_argument('--observer-off',type=Path)
    a=p.parse_args();r=report(a.run,a.build)
    rows=parse(a.run/'asteroids-events.txt');rejected=[]
    for kind,index,value,name in [('Y',3,1,'DMA pixel corruption'),('J',3,73,'late restart'),
                                   ('Q',3,0,'wrong forecast'),('P',5,9,'wrong published buffer')]:
        bad=copy.deepcopy(rows)
        row=[x for x in bad if x[0]==kind and (kind!='P' or x[2]==0x33aa8)][1]
        row[index]=value
        try:window(bad,250)
        except ValueError:rejected.append(name)
        else:raise ValueError('corrupt evidence accepted: '+name)
    if a.observer_off:r['observer_control']=neutrality(a.run,a.observer_off,a.build)
    r['rejected']=rejected;out=new_output(a.output);out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items() if k!='ownership'})

if __name__=='__main__':main()
