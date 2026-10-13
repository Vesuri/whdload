#!/usr/bin/env python3
"""Diagnostic direct-flight startup input, with an optional matched c2p delay."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from cd32_runtime import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--timing',action='store_true',help='experimental timing build instead of a delay fixture')
    p.add_argument('--nav',type=int,choices=(0,1),default=0)
    p.add_argument('--iterations', type=int, choices=(0,100000), default=0)
    a=p.parse_args()
    if a.timing:
        if a.iterations: p.error('timing fixture cannot also use the old delay tail')
        subprocess.run([sys.executable,str(ROOT/'tools/reconstruct.py'),'--timing','--output',a.output],check=True)
    else:
        subprocess.run([sys.executable,str(ROOT/'tools/intro_timing_fixture.py'),
                        '--output',a.output,'--iterations',str(a.iterations)],check=True)
    out=ROOT/a.output; slave=out/'WingCommanderCD32.Slave'
    data=bytearray(slave.read_bytes())
    # Custom3 emits "- sN". Replace the redundant standalone "-" with the
    # game's existing "l" direct-flight argument. No game instructions change.
    assert data[32+0x156a:32+0x156e]==bytes.fromhex('18fc002d')
    data[32+0x156d]=ord('l')
    if a.nav:
        at=32+0x15b2+len(b'Origin&tonic -k l s1 - m0')
        assert data[at:at+5]==bytes(5)
        data[at:at+5]=b' as1\0'
    slave.write_bytes(data)
    meta=json.loads((out/'build.json').read_text())
    meta.update(direct_flight=True,nav=a.nav,argument_immediate=0x156d,
                sha256=hashlib.sha256(data).hexdigest())
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n')

if __name__=='__main__': main()
