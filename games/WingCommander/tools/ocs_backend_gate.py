#!/usr/bin/env python3
"""Check the C3 live selection gate, with unchanged C2 pixel/display validation."""
import argparse
import json
from pathlib import Path
import shutil
from ocs_crossover_report import report
from ocs_reconstruct import new_output, require
from ocs_runtime import SIZES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--auto',required=True,type=Path)
    p.add_argument('--forced',required=True,type=Path)
    p.add_argument('--runs',nargs='+',required=True,type=Path)
    p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    roots=[a.auto,a.forced]+a.runs
    reports=[report(r) for r in roots]
    meta=[json.loads((r/'result.json').read_text()) for r in roots]
    require(meta[0]['installation']['selection']['option']=='auto' and
            meta[1]['installation']['selection']['option']=='cpu','wrong automatic/forced pair')
    require(meta[0]['arm']==meta[1]['arm']=='fast-long','pair did not use longword converter')
    for key in ('cpu','memory','scene','hunks','a4','slave_sha256','fsuae_sha256'):
        require(meta[0][key]==meta[1][key],'different pair contract: '+key)
    for checkpoint in ('install','end'):
        require((a.auto/(checkpoint+'-chip.bin')).read_bytes()==(a.forced/(checkpoint+'-chip.bin')).read_bytes(),
                'pair Chip state differs: '+checkpoint)
        memory=[(r/(checkpoint+'-fast.bin')).read_bytes() for r in (a.auto,a.forced)]
        for address,size in zip(meta[0]['hunks'],SIZES):
            off=address-meta[0]['memory_base']
            require(memory[0][off:off+size]==memory[1][off:off+size],'pair game state differs')
    scene=meta[0]['scene']
    require((a.auto/(scene+'-events.txt.sources')).read_bytes()==(a.forced/(scene+'-events.txt.sources')).read_bytes(),
            'automatic and forced source images differ')
    require(any(m['arm']=='fast-word' for m in meta),'missing word backend')
    require(any(m['cpu']=='68000' and m['arm']=='native' and m['installation']['selection']['option']=='auto' for m in meta),'missing A500 default')
    require(any(m['memory']=='slow' and m['arm']=='native' and m['installation']['selection']['option']=='cpu' for m in meta),'missing actual slow-memory fallback')
    require(any(m['arm']=='native' and m['installation']['selection']['unavailable'] for m in meta),'missing allocation-unavailable gate')
    require(any(m['arm']=='native' and m['installation']['selection']['profile']=='unknown' and m['cpu']=='68020' for m in meta),'missing unknown accelerator fallback')
    # Fresh copies of report inputs only, always below tmp. Never mutate evidence.
    bad=out/'bad-state';bad.mkdir()
    for name in ('result.json','install-audit.txt','audit.txt','adapter.bin','end-fast.bin','end-chip.bin','install-chip.bin',scene+'-events.txt'):
        shutil.copyfile(a.auto/name,bad/name)
    memory=bytearray((bad/'end-fast.bin').read_bytes())
    inst=meta[0]['installation']
    off=inst['code']-meta[0]['memory_base']+inst['symbols']['backend_state']
    memory[off:off+8]=bytes(8)
    (bad/'end-fast.bin').write_bytes(memory)
    try:report(bad)
    except ValueError as e:
        require(str(e)=='adapter code changed','wrong rejecting control: '+str(e))
    else:raise ValueError('accepted uninitialized selection state')
    result=dict(passed=True,windows=len(reports),pixel_checks=sum(r['pixel_checks'] for r in reports),
                automatic_forced_pair='exact starting/ending game hunks, all Chip and submitted source images',
                rejected=['uninitialized live selector state'],runs=reports)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='runs'}))
if __name__=='__main__':main()
