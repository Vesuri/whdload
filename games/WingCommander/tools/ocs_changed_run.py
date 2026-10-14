#!/usr/bin/env python3
"""C6 short C5 ownership windows with host-only owned instruction costs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from ocs_reconstruct import ROOT, require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',required=True,type=Path);p.add_argument('--layout',required=True,type=Path)
    p.add_argument('--output',required=True);p.add_argument('--cpu',choices=('68000','68020'),default='68020')
    p.add_argument('--off',action='store_true');p.add_argument('--views',action='store_true')
    a=p.parse_args();b=json.loads((a.build/'build.json').read_text());layout=json.loads(a.layout.read_text())
    require(b.get('changed') in ('full','blocks') and b.get('exit_probe'),'use a C6 diagnostic build')
    sy=b['symbols'];base=layout['slave']
    pairs=[('ocs_c2p_word','c2p1x1_4_c5_bm_word'),('ocs_changed_word','ocs_changed_invalidate'),
           ('c2p1x1_4_c5_bm_word','ocs_changed_word')]
    ranges=','.join(f'{base+sy[x]:x}' for pair in pairs for x in pair)
    env=dict(os.environ,SLAVE=str((a.build/'WingCommander.Slave').resolve()),WC_OCS_COST_RANGES=ranges)
    cmd=[sys.executable,str(ROOT/'tools/ocs_boot_gate.py'),'--ownership','--cpu',a.cpu,
         '--baseline','off' if a.off else 'on','--simulator','--teardown-build',str(a.build),
         '--layout',str(a.layout),'--output',a.output]
    if a.views:cmd+=['--views','--view-fields','20']
    subprocess.run(cmd,env=env,check=True)
    out=ROOT/a.output
    (out/'cost-ranges.json').write_text(json.dumps(dict(ranges=ranges,pairs=pairs,build_sha256=b['sha256']),indent=2)+'\n')

if __name__=='__main__':main()
