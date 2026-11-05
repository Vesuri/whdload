#!/usr/bin/env python3
"""Validate a completed native-reference fixture group at its encoded rate.

This launches no emulator. Use the exact listing/slave retained for the capture.
The underlying checkers enforce their native-reference case counts and results.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
import sim60_state

CHECKS={
    'input-hud':[('input_quanta_state','--listing'),('input_neutral_state','--listing'),('hud_state','--listing')],
    'knock-shake':[('knock_state',),('shake_state',)],
    'contact-terrain':[('contact_state',),('terrain_state',)],
    'motion':[('flying_state',),('special_state',),('pickup_state',)],
    'animation':[('animation_state',)],
    'post-friction':[('post_state',),('collision_state',),('terrain_friction_state','--listing')],
    'boss':[('boss_state',),('boss_path_state','--listing')],
    'linear-idle':[('linear_state','--listing'),('idle_state','--listing')],
    'input-play':[('preferences_state','--listing')],
    'geometry-flat':[('geometry_state','--listing','--boundaries'),('heading_state',),('flat_state',)],
    'projection':[('radius_state',),('project_state',),('batch_state','--listing')],
    'ai-recenter':[('ai_stack_state',),('recenter_state','--listing'),('boss_gate_state','--listing')],
    'scan-sort':[('scan_state','--flag-cases'),('shot_state','--flag-cases'),('sort_state',),('distance_state',)],
}

def validate(group,folder,listing,substeps):
    folder,listing=Path(folder),Path(listing)
    clock=sim60_state.read(folder)
    assert clock['substeps']==substeps and clock['ticks']>=101
    assert (folder/'slave.slave').read_bytes()==listing.with_suffix('.slave').read_bytes()
    results={}
    for name,*options in CHECKS[group]:
        script=Path(__file__).with_name(name+'.py')
        if not script.exists():
            raise ValueError(f'Missing checker {script.name}')
        command=[sys.executable,str(script),str(folder)]
        for option in options:
            command.append(option)
            if option=='--listing':command.append(str(listing))
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(script.parent.resolve()),str((Path.cwd()/'tools').resolve()),os.environ.get('PYTHONPATH',''))))
        run=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
        results[name]=dict(returncode=run.returncode,output=run.stdout)
        assert run.returncode==0,(name,run.stdout)
    return dict(group=group,substeps=substeps,tick=clock['ticks'],checks=results,
                scope='Private native-reference fixture results; input-play checks preferences modal state only. Not a throughput or full encounter result.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('group',choices=CHECKS)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--listing',type=Path,required=True)
    parser.add_argument('--substeps',type=int,choices=(1,2,3,4,6,12),required=True)
    args=parser.parse_args()
    print(json.dumps(validate(args.group,args.capture,args.listing,args.substeps),indent=2))
