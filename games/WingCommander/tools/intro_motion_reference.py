#!/usr/bin/env python3
"""Sample moving objects in the pinned handheld PC clip; keep all media in tmp/."""
import argparse, hashlib, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from cd32_runtime import ROOT
SHA='53942f67631e30868a214a92fae45776193306bcc805ecf27c54e5279c7be8f3'


def foreground(frame,neutral=False):
    r,g,b=[frame[:,:,i].astype(np.int16) for i in range(3)]
    if neutral:
        return (r>120)&(g>120)&(b>90)&(abs(r-g)<40)&(b>(r+g)/2-60)
    return (r>150)&(g>100)&((r-b>20)|(g-b>20))


def bounds(mask,roi):
    x0,y0,x1,y1=roi;y,x=np.where(mask[y0:y1,x0:x1])
    if len(x)<30:raise ValueError('object missing from ROI')
    return [int(x.min()+x0),int(y.min()+y0),int(x.max()+x0),int(y.max()+y0)]


def asteroid_bounds(frame):
    # Isolate the large central asteroid from the smaller neighbour and caption.
    a=frame[185:305,240:310].astype(np.int16);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    mask=(r>130)&(g>130)&(b>100)&(abs(r-g)<40)&(b>(r+g)/2-65)
    seen=set();largest=[]
    for y,x in zip(*np.where(mask)):
        if (y,x) in seen:continue
        todo=[(y,x)];seen.add((y,x));component=[]
        while todo:
            py,px=todo.pop();component.append((py,px))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    q=(py+dy,px+dx)
                    if 0<=q[0]<mask.shape[0] and 0<=q[1]<mask.shape[1] and mask[q] and q not in seen:
                        seen.add(q);todo.append(q)
        if len(component)>len(largest):largest=component
    if len(largest)<30:raise ValueError('central asteroid missing')
    points=np.array(largest);lo=points.min(0);hi=points.max(0)
    return [int(lo[1]+240),int(lo[0]+185),int(hi[1]+240),int(hi[0]+185)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path);p.add_argument('--output',required=True)
    p.add_argument('--amiga-run',type=Path,help='existing original raw-source capture; no new emulator run')
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    if hashlib.sha256(a.video.read_bytes()).hexdigest()!=SHA:raise ValueError('different recording; recalibrate before use')
    out.mkdir(parents=True);result=dict(sha256=SHA,analysis_size=[640,360],sample_hz=60,
        approximate_viewport_size=[560,224],caveat='Handheld optical reference: projected motion, not world velocity. Rolling refresh can mix adjacent poses. No audio analysis.')
    for name,start in [('ships',28.0),('explosion',29.0),('asteroids',36.2)]:
        data=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(a.video),'-an',
              '-vf','fps=60,scale=640:360','-frames:v','60','-f','rawvideo','-pix_fmt','rgb24','-'])
        if len(data)!=60*360*640*3:raise ValueError('incomplete video interval')
        frames=np.frombuffer(data,np.uint8).reshape(60,360,640,3)
        # Contacts preserve every second sample, with explicit video seconds.
        sheet=Image.new('RGB',(1920,900));draw=ImageDraw.Draw(sheet)
        for j,n in enumerate(range(0,60,2)):
            im=Image.fromarray(frames[n]).crop((0,40,560,290)).resize((320,155))
            x=j%6*320;y=j//6*180;sheet.paste(im,(x,y));draw.text((x,y+157),f'{start+n/60:.3f}',fill='white')
        sheet.save(out/(name+'.jpg'))
        masks=[foreground(f,name=='asteroids') for f in frames]
        cropped=[]
        for m in masks:
            m=m.copy();m[:55]=False;m[270:]=False;m[:,550:]=False;m[:,:15]=False;cropped.append(m)
        changes=[]
        for n,(prev,now) in enumerate(zip(cropped,cropped[1:]),1):
            # Small camera translation is allowed, but not large object motion.
            delta=min(np.count_nonzero(now[3:-3,3:-3]^np.roll(prev,(dy,dx),(0,1))[3:-3,3:-3])
                      for dx in range(-2,3) for dy in range(-2,3))
            changes.append([start+n/60,delta/max(int(now.sum()),int(prev.sum()),1)])
        record=dict(start=start,end=start+1,change_scores=changes)
        if name!='asteroids':
            candidates={}
            for threshold in (.15,.2,.25,.3):
                groups=[]
                for t,score in changes:
                    if score<=threshold:continue
                    if groups and t-groups[-1][-1]<.04:groups[-1].append(t)
                    else:groups.append([t])
                candidates[threshold]=[group[0] for group in groups]
            record['candidate_advances']=candidates
        else:
            # Manual inspection of the central asteroid, then output the exact
            # selected samples for review. Automatic colour-change clustering is
            # not a reliable frame counter here because of mixed refresh images.
            selected=[2,6,8,11,13,16]
            record['manually_selected_distinct_poses']=[start+n/60 for n in selected]
            record['selected_pose_rate']=5/((selected[-1]-selected[0])/60)
            strip=Image.new('RGB',(240*len(selected),400));d=ImageDraw.Draw(strip)
            for j,n in enumerate(selected):
                im=Image.fromarray(frames[n]).crop((235,180,315,305)).resize((240,375))
                strip.paste(im,(j*240,0));d.text((j*240,377),f'{start+n/60:.3f}',fill='white')
            strip.save(out/'asteroid-poses.jpg')
        if name=='ships':
            record['motion_bounds']=[dict(time=start+n/60,box=bounds(masks[n],(15,55,260,140))) for n in (0,4,8,12)]
        elif name=='explosion':
            record['motion_bounds']=[dict(time=start+n/60,box=bounds(masks[n],(100,70,420,250))) for n in (8,16,24,32)]
        else:
            record['motion_bounds']=[dict(time=start+n/60,box=asteroid_bounds(frames[n])) for n in (0,8)]
        result[name]=record
    if a.amiga_run:
        meta=json.loads((a.amiga_run/'result.json').read_text())
        if not meta['complete'] or not meta.get('raw_chunky') or meta['slave_sha256']!='5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986':
            raise ValueError('completed original raw capture required')
        counts={}; selected=[]; credits=[]; pictures=[]
        with (a.amiga_run/'chunky-sources.bin').open('rb') as source:
            for line in (a.amiga_run/'matrix-events.txt').read_text().splitlines():
                fields=line.split()
                if fields[0]!='C':continue
                size=int(fields[4]);raw=source.read(size)
                if len(raw)!=size:raise ValueError('truncated raw source')
                scene=int(fields[1]);n=counts.get(scene,0);counts[scene]=n+1
                seconds=int(fields[3])/(512*3546895)
                if scene==15:credits.append(seconds)
                if scene==11 and 20<=n<=36:
                    pixels=np.frombuffer(raw,np.uint8).reshape(128,320)
                    row=dict(frame=n,seconds=seconds)
                    if n in (21,22,23):
                        ys,xs=np.where(pixels[:65,:150]>90)
                        row['upper_ship_left_edge']=int(xs.min())
                    selected.append(row)
                    # Indexed values shown in grayscale for geometry only.
                    pictures.append(Image.fromarray(pixels).resize((480,240)))
            if source.read(1):raise ValueError('unconsumed source stream')
        if len(selected)!=17 or len(credits)<2:raise ValueError('motion window missing')
        sheet=Image.new('RGB',(480*4,265*5));draw=ImageDraw.Draw(sheet)
        for i,(row,im) in enumerate(zip(selected,pictures)):
            x=i%4*480;y=i//4*265;sheet.paste(im,(x,y));draw.text((x,y+242),f"frame {row['frame']}  {row['seconds']:.6f}s",fill='white')
        sheet.save(out/'amiga-motion.jpg')
        result['amiga']=dict(machine=meta['machine'],emulator_sha256=meta['emulator_sha256'],frames=selected,
            first_credit_motion_fps=(len(credits)-1)/(credits[-1]-credits[0]),
            caveat='C2P source timestamps, not display scanout; grayscale indices are not the game palette.')
    (out/'motion.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Wrote three motion contacts, selected asteroid poses and motion.json')

if __name__=='__main__':main()
