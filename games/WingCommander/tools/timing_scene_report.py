#!/usr/bin/env python3
"""Check real-flight renderer poses against their saved authoritative inputs."""
import argparse,hashlib,json,math,statistics,struct,shutil
from pathlib import Path
from cd32_runtime import ROOT
from timing_scene_check import trunc
from timing_audit_check import CPU
from flight_report import STATE_RANGES

def unpack(data,offset,fmt):return struct.unpack_from('>'+fmt,data,offset)
def percentile(values,p):return sorted(values)[int((len(values)-1)*p)] if values else None

def report(run):
    meta=json.loads((run/'result.json').read_text());sy=meta['symbols'];names=meta.get('scene_samples',[])
    if not meta['complete'] or len(names)<40:raise ValueError('at least 40 complete scene samples required')
    rows=[];checked=0;moving=0;projected=0;orienting=0;classes={};errors={};angles=[]
    native=CPU((run/"start-fast.bin").read_bytes(),meta,2)
    for name in names:
        d=(run/(name+'-data.bin')).read_bytes();s=(run/(name+'-slave.bin')).read_bytes()
        if len(d)!=0xfda0:raise ValueError('truncated data snapshot')
        hz=unpack(s,sy['timing_hz'],'I')[0];fraction=unpack(s,sy['timing_scene_fraction'],'I')[0]
        if not 0<=fraction<=hz or hz not in (50,60):raise ValueError('unbounded prediction')
        base=sy['timing_scene_saved']
        restored=(run/(name+'-restored.bin')).read_bytes()
        table=sy['timing_scene_pose_ranges'];end=sy['timing_scene_snapshot_ranges']
        canonical=bytearray(restored)
        if 'timing_scene_saved_mask' in sy:
            saved_mask=s[sy['timing_scene_saved_mask']:sy['timing_scene_saved_mask']+64]
            for slot in range(64):
                if not saved_mask[slot]:continue
                cursor=base+120*slot
                for at in range(table,end,4):
                    relative,longs=unpack(s,at,'hH');length=(longs+1)*4;offset=relative+0x7ffe
                    # Angles, effect indices and projection words are separate
                    # parallel arrays, not interleaved components per object.
                    parts=3 if relative in (0x157a,0x245e) else 2 if relative==0x4078 else 1
                    width=length//(64*parts)
                    for part in range(parts):
                        dst=offset+part*64*width+slot*width
                        canonical[dst:dst+width]=s[cursor:cursor+width];cursor+=width
                if cursor!=base+120*(slot+1):raise ValueError('bad packed pose size')
        else:
            cursor=base
            for at in range(table,end,4):
                relative,longs=unpack(s,at,'hH');length=(longs+1)*4;offset=relative+0x7ffe
                canonical[offset:offset+length]=s[cursor:cursor+length];cursor+=length
        if canonical!=restored:raise ValueError(f'{name}: saved state not restored')
        mask=s[sy['timing_scene_predictable']:sy['timing_scene_predictable']+64]
        valid=unpack(s,sy['timing_scene_valid'],'H')[0]
        if unpack(s,sy['timing_scene_staged'],'H')[0]!=1:raise ValueError('not a staged render')
        tick=unpack(d,0x914c,'H')[0];view=unpack(d,0x3896,'h')[0]
        rr=dict(tick=tick,data=d,restored=restored,slave=s,base=base,mask=mask,positions=[],predicted=[],types=[])
        for slot in range(61):
            kind=unpack(d,0x96fe+2*slot,'h')[0];rr['types'].append(kind)
            pos=unpack(restored,0x919a+12*slot,'3i');shown=unpack(d,0x919a+12*slot,'3i')
            vel=unpack(s,sy['timing_scene_velocities']+12*slot,'3i')
            original=unpack(s,sy['timing_scene_positions']+12*slot,'3i')
            enabled=bool(valid and mask[0] and mask[slot] and kind>=3 and kind!=7 and original==pos and 0<=view<=3)
            want=tuple(((p+trunc(v*fraction,hz)+2**31)%2**32)-2**31 for p,v in zip(pos,vel)) if enabled else pos
            if shown!=want:raise ValueError(f'{name} slot {slot} class {kind}: rendered {shown}, expected {want}')
            rr['positions'].append(pos);rr['predicted'].append(tuple(p+v for p,v in zip(pos,vel)))
            if enabled and fraction:
                checked+=1;classes[str(kind)]=classes.get(str(kind),0)+1
            if rows and rows[-1]['tick']==tick and kind and kind==rows[-1]['types'][slot]:
                old=rows[-1]['data']
                if shown!=unpack(old,0x919a+12*slot,'3i'):
                    moving+=1
                    x=unpack(d,0xa45c+2*slot,'h')[0];oldx=unpack(old,0xa45c+2*slot,'h')[0]
                    y=unpack(d,0xabe8+2*slot,'h')[0];oldy=unpack(old,0xabe8+2*slot,'h')[0]
                    if x!=-32767 and oldx!=-32767 and (x,y)!=(oldx,oldy):projected+=1
                if slot and d[0xa148+12*slot:0xa154+12*slot]!=old[0xa148+12*slot:0xa154+12*slot]:orienting+=1
        if rows and rows[-1]['tick']==tick:
            for key,(offset,length) in STATE_RANGES.items():
                if key in ('positions','forward_vectors','draw_counter'):continue
                if restored[offset:offset+length]!=rows[-1]['restored'][offset:offset+length]:
                    raise ValueError(f'{name}: gameplay field {key} changed between updates')
            if restored[0x919a:0x919a+61*12]!=rows[-1]['restored'][0x919a:0x919a+61*12]:
                raise ValueError(f'{name}: authoritative positions changed between updates')
        if rows and (tick-rows[-1]['tick'])&0xffff==1:
            prior=rows[-1]
            native.write(native.data,prior['data'])
            for n,offset in enumerate((0x919a,0xa148,0xb450,0xb750,0x9d6c)):
                native.write(native.data+offset,prior['restored'][offset:offset+768])
            for slot in range(61):
                kind=rr['types'][slot]
                if kind>=3 and kind!=7 and kind==prior['types'][slot] and mask[slot] and prior['mask'][slot]:
                    error=math.dist(prior['predicted'][slot],rr['positions'][slot])/256
                    errors.setdefault(str(kind),[]).append(error)
                    if slot:
                        for axis,entry in enumerate((0x2acb2,0x2acf2,0x2ad32)):
                            rate=unpack(prior['slave'],sy['timing_scene_angles']+128*axis+2*slot,'h')[0]
                            if rate:native.run(entry,struct.pack('>hh',rate,slot))
                        basis_errors=[]
                        for index,offset in enumerate((0xa148,0xb450,0xb750),1):
                            forecast=unpack(native.read(native.data+offset+12*slot,12),0,'3i')
                            actual=unpack(restored,offset+12*slot,'3i')
                            norm=math.sqrt(sum(v*v for v in forecast)*sum(v*v for v in actual))
                            if norm:basis_errors.append(math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(forecast,actual))/norm)))))
                        if basis_errors:angles.append(max(basis_errors))
        rows.append(rr)
    native.close()
    if not checked or not moving or not projected:raise ValueError('no visible between-tick prediction demonstrated')
    return dict(run=run.name,pictures=len(rows),checked_predictions=checked,classes=classes,
        between_tick_object_moves=moving,between_tick_projected_moves=projected,between_tick_orientation_changes=orienting,
        next_tick_basis_error_degrees=dict(count=len(angles),median=statistics.median(angles) if angles else None,p95=percentile(angles,.95),maximum=max(angles,default=0)),
        next_tick_position_error_km={k:dict(count=len(v),median=statistics.median(v),p95=percentile(v,.95),maximum=max(v)) for k,v in errors.items()},
        hashes={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for stem in names for name in (stem+'-data.bin',stem+'-slave.bin',stem+'-restored.bin')})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--negative-controls',action='store_true');a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    rows=[report(r) for r in a.runs]
    controls=[]
    if a.negative_controls:
        source=a.runs[0];meta=json.loads((source/'result.json').read_text());stem=meta['scene_samples'][0]
        for label,suffix,offset,expected in [('pose','data',0x919a,'rendered'),('restore','restored',0x96fe,'not restored')]:
            target=out.parent/(out.stem+'-negative-'+label);target.mkdir()
            for name in ['result.json','start-fast.bin']+[stem+'-'+v+'.bin' for v in ('data','slave','restored')]:
                shutil.copyfile(source/name,target/name)
            path=target/(stem+'-'+suffix+'.bin');data=bytearray(path.read_bytes());data[offset]^=1;path.write_bytes(data)
            try:report(target)
            except ValueError as error:
                if expected not in str(error):raise
                controls.append(dict(control=label,rejected=str(error)))
            else:raise AssertionError('negative control accepted')
    out.write_text(json.dumps(dict(runs=rows,negative_controls=controls,scope='renderer input/projection correctness; breakpoint-separated samples are not frame-rate measurements'),indent=2)+'\n')
    for r in rows:print({k:v for k,v in r.items() if k!='hashes'})
if __name__=='__main__':main()
