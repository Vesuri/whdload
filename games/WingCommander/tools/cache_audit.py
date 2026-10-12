#!/usr/bin/env python3
"""Separate terminating VERIFY cache boot; never supplies performance timings."""
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path
from cd32_runtime import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--slave',required=True)
    p.add_argument('--machine',choices=['a1200-fast','a1200-030','a1200-040','a1200-060'],required=True)
    p.add_argument('--options',default='');a=p.parse_args()
    out=(ROOT/a.output).resolve();slave=(ROOT/a.slave).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new output below tmp/ required')
    build=json.loads((slave.parent/'build.json').read_text())
    if not build.get('cache_audit'):raise ValueError('VERIFY cache audit build required')
    if hashlib.sha256(slave.read_bytes()).hexdigest()!=build['sha256']:raise ValueError('audit build digest mismatch')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('fixed audit configuration required')
    out.mkdir(parents=True);os.chdir(ROOT)
    env=dict(os.environ,FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',SLAVE=str(slave),
             AMIGA_SETUP=a.machine,INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',
             WHD_ARGS='CUSTOM5=0 FILELOG '+a.options,WARP='0',NTSC='0',DEBUG='0',
             DETERMINISTIC='1',WINDOW='front',SILENT='1',JOY0='none',JOY1='none')
    for key in ('WC_OBSERVER_CONFIG','WC_OBSERVER_OUTPUT','WC_MATRIX_CONFIG','WC_MATRIX_DIR'):
        env.pop(key,None)
    try:
        subprocess.run(['/bin/bash','amiga/run.sh'],env=env,check=True)
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            for path in (out/'run').glob('boot.*/dh*/**/*'):
                if path.is_file() and 'log' in path.name.lower() and path.suffix!='.uaem':
                    data=path.read_bytes()
                    m=re.search(rb'WC_CACHE attn=([0-9a-fA-F]+) setup=([0-9a-fA-F]+) cache_api=([0-9a-fA-F]+) cacr=([0-9a-fA-F]+)',data)
                    if m:
                        result=dict(zip(('attn','setup','cache_api','cacr'),[int(x,16) for x in m.groups()]))
                        result.update(machine=a.machine,options=a.options,complete=True,
                                      slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),
                                      emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
                        (out/'audit.log').write_bytes(data)
                        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
                        print(json.dumps(result));return
            time.sleep(1)
        raise TimeoutError('VERIFY audit did not produce its success record')
    finally:subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__':main()
