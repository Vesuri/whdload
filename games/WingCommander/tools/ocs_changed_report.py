#!/usr/bin/env python3
"""C6 equal-reservation comparison, matched images and exclusive CPU costs."""
import argparse
import json
import itertools
from pathlib import Path
from ocs_baseline_report import parse, distribution
from ocs_publication_report import report as correctness
from ocs_reconstruct import new_output, require

HZ=28375160/8*512

def samples(root,scene,rows=None):
    rows=parse(root/(scene+'-events.txt')) if rows is None else rows;hs=[r for r in rows if r[0]=='H']
    raw=(root/(scene+'-events.txt.sources')).read_bytes();offset=0;result=[]
    end=next(r[1] for r in rows if r[0]=='E')
    begin=next(r for r in rows if r[0]=='B')
    require(begin[2:4]==[28375160,512] and begin[4] in (128,256),'uncalibrated PAL clock')
    fields=[r[1] for r in rows if r[0]=='F'];prev=begin[1]
    for field in fields:
        require(field-prev in (227*312*512,227*313*512),'field duration');prev=field
    for index,h in enumerate(hs):
        frame=raw[offset:offset+h[3]];offset+=h[3]
        v=2166136261
        for byte in frame:v=((v^byte)*16777619)&0xffffffff
        require(v==h[4],'source stream hash mismatch')
        limit=hs[index+1][1] if index+1<len(hs) else end
        done=[r for r in rows if r[0]=='P' and r[2]==0x32e06 and h[1]<=r[1]<limit]
        if not done:
            require(index==len(hs)-1,'missing interior completion')
            continue
        require(len(done)==1,'completion pairing')
        k=[r for r in rows if r[0]=='K' and r[1]==done[0][1]]
        require(len(k)==1,'missing instruction costs')
        pub=next((r for r in rows if r[0]=='P' and r[2]==0x33aa8 and r[1]>done[0][1]),None)
        display=next((r for r in rows if r[0]=='D' and pub and r[1]>pub[1] and r[3]==pub[5]),None)
        if display is None:
            require(index==len(hs)-1,'missing interior display')
            continue
        require(all(x>=0 for x in k[0][2:]),'negative instruction charge')
        require(sum(k[0][2:])<=done[0][1]-h[1],'instruction costs exceed conversion')
        result.append(dict(source=frame,display=display[1],conversion=done[0][1]-h[1],cost=k[0][2:]))
    require(offset==len(raw),'source stream length')
    return result


def compare(runs,scene):
    ss=[samples(root,scene) for root,build in runs]
    # Capturing one field at the native milestone can finish one submission.
    # Permit only that single boundary image, never search interior workloads.
    trims=next((t for t in itertools.product((0,1),repeat=len(ss))
                if all(x[t[i]]['source']==ss[0][t[0]]['source'] for i,x in enumerate(ss))),None)
    require(trims is not None,'no common initial image within one boundary submission')
    ss=[x[t:] for x,t in zip(ss,trims)]
    n=0
    for items in zip(*ss):
        if any(i['source']!=items[0]['source'] for i in items):break
        n+=1
    require(n>=4,'too few byte-identical completed/displayed images: '+scene+' '+str(n))
    arms=[]
    for (root,build),values in zip(runs,ss):
        values=values[:n];b=json.loads((build/'build.json').read_text())
        intervals=[(q['display']-p['display'])/HZ*1000 for p,q in zip(values,values[1:])]
        arms.append(dict(run=root.name,backend=b['backend'],changed=b['changed'],images=n,
                         fps=(n-1)*HZ/(values[-1]['display']-values[0]['display']),
                         interval_ms=distribution(intervals),
                         conversion_ms=distribution([v['conversion']/HZ*1000 for v in values]),
                         exclusive_cpu_ms={name:distribution([v['cost'][i]/HZ*1000 for v in values]) for i,name in enumerate(('full_adapter','comparison_history_staging_adapter','kalms_leaf'))}))
    return dict(scene=scene,boundary_images_trimmed=trims,matched_images=n,arms=arms)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',nargs=2,action='append',metavar=('RUN','BUILD'),required=True)
    p.add_argument('--output',required=True);a=p.parse_args()
    runs=[(Path(r),Path(b)) for r,b in a.run];out=new_output(a.output)
    metas=[json.loads((r/'result.json').read_text()) for r,b in runs]
    builds=[json.loads((b/'build.json').read_text()) for r,b in runs]
    for key in ('machine','effective','fsuae_sha256','hunks','slave','a4'):
        require(all(m[key]==metas[0][key] for m in metas),'different comparison setup: '+key)
    require(len({b['bytes'] for b in builds})==1,'unequal reservation')
    palettes=[(r/'credits-h0.bin').read_bytes()[0x331dc:0x331fc] for r,b in runs]
    require(all(p==palettes[0] for p in palettes),'different initial native palette')
    for (r,b),m,build in zip(runs,metas,builds):
        sy=build['symbols'];base=m['slave']
        names=('ocs_c2p_word','c2p1x1_4_c5_bm_word','ocs_changed_word','ocs_changed_invalidate','c2p1x1_4_c5_bm_word','ocs_changed_word')
        expected=','.join(f'{base+sy[name]:x}' for name in names)
        cfg=json.loads((r/'cost-ranges.json').read_text())
        require(cfg['ranges']==expected and cfg['build_sha256']==build['sha256'],'wrong instruction ranges')
        for scene in ('asteroids','fire'):
            values=samples(r,scene)
            require(len(values)>=4,'too few complete measurements')
            costs=[sum(x['cost'][i] for x in values) for i in range(3)]
            if build['backend']=='native':require(costs==[0,0,0],'CPU converter in native arm')
            elif build['changed']=='blocks':require(costs[0]==0 and costs[1]>0 and costs[2]>0,'changed path not measured')
            else:require(costs[0]>0 and costs[1]==0 and costs[2]>0,'full path not measured')
    checks=[correctness(r,b) for r,b in runs]
    result=dict(passed=True,machine=metas[0]['machine'],correctness=checks,
                history_bytes=128000,slave_bytes=builds[0]['bytes'],
                comparisons=[compare(runs,'asteroids')],
                flight_scope='Correctness and inclusive per-run conversion costs only; prior intro windows advance unequal world histories, so no matched flight speed claim.',
                flight=[dict(run=r.name,completed=len(v),conversion_ms=distribution([x['conversion']/HZ*1000 for x in v]),
                    exclusive_cpu_ms={name:distribution([x['cost'][i]/HZ*1000 for x in v]) for i,name in enumerate(('full_adapter','comparison_history_staging_adapter','kalms_leaf'))})
                    for r,b in runs for v in [samples(r,'fire')]])
    import copy
    rejected=[];root=runs[-1][0];rows=parse(root/'asteroids-events.txt')
    for name in ('missing costs','inflated costs','wrong source hash'):
        bad=copy.deepcopy(rows)
        if name=='missing costs':bad=[r for r in bad if r[0]!='K']
        elif name=='inflated costs':next(r for r in bad if r[0]=='K')[2]=1<<63
        else:next(r for r in bad if r[0]=='H')[4]^=1
        try:samples(root,'asteroids',bad)
        except ValueError:rejected.append(name)
        else:raise ValueError('bad measurement accepted: '+name)
    result['rejected']=rejected
    out.write_text(json.dumps(result,indent=2)+'\n')
    for scene in result['comparisons']:
        print(scene['scene'],scene['matched_images'],[(x['backend'],x['changed'],round(x['fps'],3)) for x in scene['arms']])

if __name__=='__main__':main()
