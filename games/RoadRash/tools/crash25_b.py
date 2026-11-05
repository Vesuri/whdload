import os,json,subprocess,sys
from pathlib import Path
from harness_a import ROOT
base=json.loads((ROOT/'tools/fixtures/lap.json').read_text());root=ROOT/'tmp/b5-crash-search';root.mkdir(exist_ok=True)
for shift,wiggle in [(0,False),(200,True),(400,True),(0,True)]:
    tape=dict(base);tape['end_field']=2400;tape['screenshots']=[1400,1800,2200,2400]
    tape['events']=[[100,'JOY2_UP',1]]+([[600,'JOY2_RIGHT',1],[620,'JOY2_RIGHT',0],[800,'JOY2_LEFT',1],[820,'JOY2_LEFT',0]] if wiggle else [])+[[1100+shift,'JOY2_RIGHT',1],[1140+shift,'JOY2_RIGHT',0],[1140+shift,'JOY2_LEFT',1],[1500+shift,'JOY2_LEFT',0],[2300,'JOY2_UP',0]]
    path=root/f'tape-{shift}-{wiggle}.json';path.write_text(json.dumps(tape,indent=2))
    out=root/f'run-{shift}-{wiggle}'
    env=dict(os.environ,RR_B='1',DEBUG_PORT='3094',SLAVE=str(ROOT/'tmp/b5-25-build/RoadRash-verify.slave'),EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
    with (root/f'run-{shift}-{wiggle}.log').open('w') as log:subprocess.run([sys.executable,str(ROOT/'tools/replay_a.py'),str(out),'--tape',str(path),'--sample-step','10'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    x=json.loads((out/'replay.json').read_text());print(shift,wiggle,x['crash_onsets_sampled'],flush=True)
    if x['crash_onsets_sampled']:
        (root/'accepted.txt').write_text(str(out));break
else:raise RuntimeError('No crash found')
