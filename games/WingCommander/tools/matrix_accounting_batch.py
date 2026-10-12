#!/usr/bin/env python3
"""Capture cache-audited bare/idle/DMA pairs for an explicit matrix plan in fresh tmp output."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from cd32_runtime import ROOT
from matrix_idle_check import check as idle_check
from matrix_dma_check import check as dma_check
from matrix_raw_check import check as raw_check, compare as neutral_check
from matrix_dma_effect import compare as dma_effect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path,help='JSON list of {name,reference} completed layout/cell captures')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--audit-slave',required=True)
    parser.add_argument('--ports',type=int,nargs=2,default=[2456,2457])
    args=parser.parse_args()
    root=(ROOT/args.output).resolve()
    if (ROOT/'tmp').resolve() not in root.parents or root.exists():raise ValueError('new tmp batch directory required')
    if len(set(args.ports))!=2 or any(not 1024<=p<=65535 for p in args.ports):raise ValueError('two distinct debugger ports required')
    plan=json.loads((ROOT/args.plan).read_text())
    names=set()
    for cell in plan:
        name=cell['name']
        if not re.fullmatch(r'[a-z0-9-]+',name) or name in names:raise ValueError('unique simple cell names required')
        names.add(name)
        meta=json.loads((ROOT/cell['reference']).read_text())
        if not meta['complete']:raise ValueError('completed reference required')
        cell['metadata']=meta
    if not plan:raise ValueError('nonempty matrix plan required')
    root.mkdir()
    (root/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    def lane(cells,port):
        results=[]
        for cell in cells:
            name=cell['name'];meta=cell['metadata'];out=root/name;out.mkdir()
            env=dict(os.environ,DEBUG_PORT=str(port))
            commands=[]
            def run(tool,arguments,label):
                command=[sys.executable,'tools/'+tool]+arguments
                commands.append(command)
                (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
                print(name+': '+label,flush=True)
                with (out/(label+'.log')).open('w') as log:
                    subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            def save(name,data):
                (out/name).write_text(json.dumps(data,indent=2)+'\n')
            try:
                options=['--machine',meta['machine'],'--options',meta['options']]
                nommu=bool(meta.get('nommu_core'))
                run('cache_audit.py',options+(['--nommu-core'] if nommu else [])+
                    ['--slave',args.audit_slave,'--output',str((out/'audit').relative_to(ROOT))],'audit')
                selector=['--nommu-core'] if nommu else ['--mmu-core'] if meta.get('mmu_core') else []
                common=options+selector+['--no-profiles','--warp','--raw-chunky',
                    '--audit',str((out/'audit/result.json').relative_to(ROOT)),'--layout',cell['reference']]
                for arm,flags in (('bare',[]),('idle',['--idle']),('dma',['--idle','--dma'])):
                    run('matrix_capture.py',common+flags+['--output',str((out/arm).relative_to(ROOT))],arm)
                    save(arm+'-raw.json',raw_check(out/arm))
                    if arm!='bare':save(arm+'-idle.json',idle_check(out/arm))
                save('idle-neutrality.json',neutral_check(out/'bare',out/'idle'))
                save('dma-report.json',dma_check(out/'dma'))
                effect=dma_effect(out/'idle',out/'dma');save('dma-effect.json',effect)
                result=dict(name=name,complete=True,dma_records_equal_except_clock=effect['records_equal_except_clock'])
            except Exception as error:
                result=dict(name=name,complete=False,error=type(error).__name__+': '+str(error))
            save('result.json',result);results.append(result)
            print(name+': '+json.dumps(result),flush=True)
        return results
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(lane,plan[i::2],args.ports[i]) for i in range(2)]
        results=[result for job in jobs for result in job.result()]
    (root/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    if not all(r['complete'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
