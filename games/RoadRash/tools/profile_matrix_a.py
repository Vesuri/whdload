#!/usr/bin/env python3
"""Flat instruction profiles on 030/040/060; same race-field window as the 020 capture."""
import argparse,json,os,signal,subprocess,sys,time
from matrix_a import config,cleanup,ROOT
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('cells',nargs='*');args=ap.parse_args()
    root=Path(args.out).resolve();root.mkdir(parents=True,exist_ok=True);results=[]
    for cell in args.cells or ('030-50+cache','040-25','060-50'):
        out=root/cell
        if out.exists():raise RuntimeError('output exists')
        out.mkdir()
        with (out/'run.log').open('w') as log:
            p=subprocess.Popen([sys.executable,str(ROOT/'tools/profile_a.py'),str(out),'--kind','aprof'],env=config(cell),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:rc=p.wait(timeout=180)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait();rc=124
            finally:cleanup(out)
        results.append(dict(cell=cell,returncode=rc));print(results[-1],flush=True)
        (root/'profiles.json').write_text(json.dumps(results,indent=2)+'\n')
    if any(x['returncode'] for x in results):sys.exit(1)

if __name__=='__main__':main()
