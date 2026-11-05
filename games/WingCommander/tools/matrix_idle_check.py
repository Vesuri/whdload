#!/usr/bin/env python3
"""Integrate STOP transitions per scene and compare the independent wait-loop counter."""
import argparse
import json
from pathlib import Path
from matrix_scene_report import report as scene_report

CLOCK = 512*3546895


def check(run):
    meta=json.loads((run/'result.json').read_text())
    if not meta.get('idle'):raise ValueError('idle-enabled capture required')
    scenes=scene_report(run)['scenes']
    cuts=[]
    for line in (run/'matrix-events.txt').read_text().splitlines():
        p=line.split()
        if p[0]=='B':cuts.append((int(p[1]),int(p[4])))
    current=-1;last=None;state=False;stopped=0;entries=0;schema=None
    wait_before=0;calls_before=0;pc_before=None;output=[]
    memory=(run/'fast.bin').read_bytes()
    for offset in (0x34074,0x3408e):
        at=meta['hunks'][0]-0x200000+offset
        if memory[at:at+2]!=bytes.fromhex('4e72'):raise ValueError('game STOP entry opcode changed')
    for line in (run/'idle-events.txt').read_text().splitlines():
        p=line.split()
        if p[0]=='B':
            if len(p) not in (6,8):raise ValueError('malformed idle scene boundary')
            if schema is None:schema=len(p)
            if len(p)!=schema:raise ValueError('mixed idle record schema')
            scene,at,value,wait,calls=map(int,p[1:6])
            pc_counts=list(map(int,p[6:])) if len(p)==8 else None
            if pc_counts is not None and any(n<0 for n in pc_counts):raise ValueError('invalid STOP PC count')
            if scene!=current+1 or scene>=len(cuts) or (scene,at)!=cuts[scene]:
                raise ValueError('idle scene boundary differs from publication ledger')
            if value not in (0,1) or min(wait,calls)<0:
                raise ValueError('invalid idle scene state/counters')
            if last is None:
                if scene!=0 or wait or calls or (pc_counts and any(pc_counts)):
                    raise ValueError('invalid initial idle counters')
                state=bool(value)
            else:
                if at<last or bool(value)!=state:raise ValueError('missing/nonmonotonic STOP transition')
                if state:stopped+=at-last
                units=scenes[current]['units']
                waited=wait-wait_before;call_count=calls-calls_before
                if not 0<=waited<=stopped<=units or call_count<0:
                    raise ValueError('STOP wait/state accounting exceeds scene or disagrees')
                pc_delta=[a-b for a,b in zip(pc_counts,pc_before)] if pc_counts is not None and pc_before is not None else None
                if pc_delta is not None and (min(pc_delta)<0 or (current>0 and sum(pc_delta)!=call_count+entries)):
                    raise ValueError('STOP instruction count differs from wait calls plus entries')
                output.append(dict(stop_pc_counts=pc_delta,scene=scenes[current]['scene'],scene_units=units,
                    stopped_units=stopped,stopped_seconds=stopped/CLOCK,stopped_share=stopped/units,
                    stop_entries=entries,wait_loop_units=waited,wait_loop_calls=call_count,
                    stopped_outside_wait_loop_units=stopped-waited))
            current=scene;last=at;stopped=0;entries=0
            wait_before=wait;calls_before=calls;pc_before=pc_counts
        elif p[0]=='T':
            if len(p)!=3:raise ValueError('malformed STOP transition')
            at,value=map(int,p[1:])
            if not 0<=current<34 or at<last or value not in (0,1) or bool(value)==state:
                raise ValueError('invalid/redundant STOP transition')
            if state:stopped+=at-last
            state=bool(value);entries+=int(state);last=at
        else:raise ValueError('unknown idle record')
    if current!=34 or len(output)!=34:raise ValueError('incomplete idle coverage')
    return dict(stop_state_accounting_pass=True,wait_loop_lower_bound_pass=True,
                game_stop_instruction_count_pass=all(s["stop_pc_counts"] is not None for s in output[1:]),
                exact_wait_loop_agreement=all(s['stopped_outside_wait_loop_units']==0 for s in output),
                scenes=output,validated_baseline=False,
                limitations=['STOP state is CPU idle; executing busy waits are not included.',
                             'The wait-loop counter excludes the initial STOP instruction latency.',
                             'Any stopped time outside the wait loop is retained explicitly.',
                             'A separate same-binary recording-off comparison must validate neutrality.'])


def compare_profile(run,profile):
    from matrix_report import report as profile_report, read_aprof
    measured=check(run)
    profile_report(profile)
    left=json.loads((run/'result.json').read_text())
    right=json.loads((profile/'result.json').read_text())
    for key in ('machine','options','audit_cacr','hunks','slave','slave_sha256'):
        if left[key]!=right[key]:raise ValueError('unmatched STOP profile: '+key)
    if (run/'matrix-events.txt').read_bytes()!=(profile/'matrix-events.txt').read_bytes():
        raise ValueError('STOP profile must have identical scene/publication/census ledger')
    pcs=[left['hunks'][0]+offset for offset in (0x34074,0x3408e)]
    memory=(profile/'fast.bin').read_bytes()
    for pc in pcs:
        if memory[pc-0x200000:pc-0x200000+2]!=bytes.fromhex('4e72'):
            raise ValueError('profiled game STOP opcode differs')
    rows=[]
    for i,scene in enumerate(measured['scenes']):
        if i==0:continue # Game code is not loaded throughout reset.
        header,records,_,_,_=read_aprof(profile/f'scene-{i:02d}.aprof')
        if header.get('source_pc_stable')!=1:raise ValueError('stable executing-PC profile required')
        stops=[p for p in records if p[0] in pcs]
        count=sum(p[2] for p in stops)
        if count!=scene['stop_entries']+scene['wait_loop_calls']:
            raise ValueError('independent STOP instruction count disagrees')
        rows.append(dict(scene=scene['scene'],stop_instruction_count=count,
                         instruction_body_units=sum(p[1] for p in stops),
                         stopped_state_units=scene['stopped_units']))
    return dict(independent_game_stop_count_pass=True,scenes=rows,
                scope='Independent instruction counts after game startup; instruction-body and stopped-state clocks have different boundaries.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--profile-control',type=Path)
    args=parser.parse_args()
    result=check(args.run)
    if args.profile_control:result['profile_crosscheck']=compare_profile(args.run,args.profile_control)
    print(json.dumps(result,indent=2))
