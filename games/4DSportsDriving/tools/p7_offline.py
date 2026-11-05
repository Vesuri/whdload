#!/usr/bin/env python3
"""P7 exact controls and per-update flat-road Z accounting; no runtime edits."""
import gzip,runpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
OUT=Path('tmp/prof/p7-session1')
read_bytes=Path.read_bytes
write_text=Path.write_text
def compressed(p):
    return read_bytes(p) if p.exists() else gzip.decompress(read_bytes(Path(str(p)+'.gz')))
Path.read_bytes=compressed
# Historical controls normally overwrite root reports; retain fresh evidence instead.
def redirected(p,data,*args,**kw):
    if p.parent==Path('tmp/prof') and p.name.startswith('coupled-course'):
        p=OUT/p.name
    return write_text(p,data,*args,**kw)
Path.write_text=redirected
if __name__=='__main__':
    import os
    os.environ['COUPLED_REPORT_DIR']=str(OUT)
    for hz in (20,50):
        for phase in ('nominal','minus64','plus64'):
            sys.argv=['control','baseline',phase]
            runpy.run_path('tools/coupled_course'+('20' if hz==20 else '')+'_check.py',run_name='__main__')
    from coupled_vehicle_core import seed,advance,summarize
    from native_contact_response import rotate,sine
    reports={}
    for hz,cap in [(20,'natural-crest20'),(50,'crest-d9e7903')]:
        b,read,param=seed('tmp/prof/'+cap);rows=[]
        while b['contact']['entry'][0]<=hz*9:
            t=b['contact']['entry'][0];before=b['contact']['position'][:]
            b,rec=advance(b,hz,read,param)
            c=rec['contact'];e=c['entry'];d=rec['engine']['distance'];out=c['output']
            if .2<=t/hz<=1.6:
                rows.append(dict(tick=t,time=t/hz,pitch=e[2],speed=summarize(b)['speed'],intended=d,rotated=rotate([0,0,d],e[4:13])[2],applied=out['position'][2]-before[2],matrix=e[4:13],centroid_carries=out['centroid_carries']))
        reports[str(hz)]=dict(rows=rows,at9=summarize(b))
    (OUT/'z-ledger.json').write_text(json.dumps(reports,indent=2)+'\n')
    print('Z difference',reports['50']['at9']['position'][2]-reports['20']['at9']['position'][2])
    print('sine256',sine(256),'first rows',reports['20']['rows'][:3],reports['50']['rows'][:3])
