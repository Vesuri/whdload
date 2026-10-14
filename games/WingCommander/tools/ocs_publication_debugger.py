#!/usr/bin/env python3
"""Extend the pinned C2 local instrument with read-only C5 DMA pixel checks."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from ocs_reconstruct import ROOT, new_output, require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',default='tmp/p13c2-debugger-measured')
    p.add_argument('--output',required=True);a=p.parse_args()
    source=Path(a.source);out=new_output(a.output)
    for line in (ROOT/'manifest/ocs-publication-debugger.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        path,digest=line.split('\t')
        require(hashlib.sha256((source/path).read_bytes()).hexdigest()==digest,'changed C2 input: '+path)
    shutil.copytree(source,out,ignore=shutil.ignore_patterns('.git'))
    shutil.copyfile(ROOT/'tools/ocs_observer.inc',out/'src/wc_ocs_observer.inc')
    custom=out/'src/custom.cpp'
    code=custom.read_text();anchor='wc_ocs_fetch(bpladdr,plane);'
    require(code.count(anchor)==1,'missing optimized DMA span hook')
    code=code.replace(anchor,'for (int wc_n=0;wc_n<nwords;++wc_n) wc_ocs_fetch(bpladdr+2*wc_n,plane);')
    custom.write_text(code)
    # A restored build tree can have object timestamps ahead of its includes.
    (out/'src/newcpu.cpp').touch()
    subprocess.run(['/usr/bin/make','-j4','fs-uae'],cwd=out,env=dict(os.environ,TMPDIR=str(out)),check=True)
    print(hashlib.sha256((out/'fs-uae').read_bytes()).hexdigest())

if __name__=='__main__':main()
