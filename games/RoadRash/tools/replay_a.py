#!/usr/bin/env python3
import argparse,json,os
from harness_a import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--tape',default=str(ROOT/'tools/fixtures/lap.json'))
    ap.add_argument('--normal',action='store_true');ap.add_argument('--sample-step',type=int,default=2)
    args=ap.parse_args();tape=json.loads(Path(args.tape).read_text())
    slave=Path(os.environ.get('SLAVE',ROOT/'tmp/build'/('RoadRash.slave' if args.normal else 'RoadRash-verify.slave'))).resolve();os.environ['SLAVE']=str(slave)
    if (Path(args.out)/'replay.json').exists():raise RuntimeError('choose a fresh output directory')
    s=Session(args.out)
    try:
        initial=route(s);address=None if args.normal else stats_address(s);before=None if args.normal else counters(s,address)
        if os.environ.get('RR_INITIAL_DUMP'):
            (s.out/'initial-rng.bin').write_bytes(read_bytes(s,0x90000,0x88))
            (s.out/'initial-actors.bin').write_bytes(read_bytes(s,0xa5d60,0x1180))
        samples=[initial];events={}
        for f,event,v in tape['events']:events.setdefault(f,[]).append((event,v))
        times=sorted(set(range(100,tape['end_field']+1,args.sample_step))|set(events)|set(tape['screenshots']))
        for target in times:
            if target in tape['screenshots']:
                advance(s,target-2);s.shot(f'race-{target:04d}.png')
                if field(s)!=target:raise RuntimeError('screenshot field boundary mismatch')
            else:advance(s,target)
            snap=snapshot(s)
            samples.append(snap)
            for event,v in events.get(target,[]):s.input(event,v)
            if target%100==0:print(target,'x',snap['lateral'],'rank',snap['rank_displayed'],'crash',snap['crash_state'],flush=True)
        crashes=[b['field'] for a,b in zip(samples,samples[1:]) if a['crash_state']<0<=b['crash_state']]
        result=dict(provenance=provenance(slave,s),tape=tape,initial=initial,samples=samples,crash_onsets_sampled=crashes,sample_step=args.sample_step,before=before,after=None if args.normal else counters(s,address))
        if os.environ.get('RR_B'):result['b_stats']=b_counters(s)
        (s.out/'replay.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:s.quit()

if __name__=='__main__':main()
