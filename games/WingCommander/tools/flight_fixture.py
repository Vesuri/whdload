#!/usr/bin/env python3
"""Diagnostic direct-flight startup input, with an optional matched c2p delay."""
import argparse, hashlib, json, subprocess, sys, re, struct
from pathlib import Path
from cd32_runtime import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--release',action='store_true',help='public options with integrated renderer')
    modes.add_argument('--timing',action='store_true',help='experimental timing build instead of a delay fixture')
    p.add_argument('--flight-verify',action='store_true')
    p.add_argument('--flight-control',action='store_true')
    p.add_argument('--timing-verify',action='store_true')
    p.add_argument('--view-control',action='store_true',help='D3 diagnostic native clear/composition control; release only')
    p.add_argument('--frame-stats',action='store_true',help='diagnostic frame-part recorder')
    p.add_argument('--schedule',choices=('normal','slow','one-field'),default='normal',help='VERIFY-only render schedule')
    p.add_argument('--nav',type=int,choices=(0,1),default=0)
    p.add_argument('--iterations', type=int, choices=(0,100000), default=0)
    a=p.parse_args()
    if (a.flight_verify or a.flight_control) and not a.timing:p.error('flight diagnostics require --timing')
    if a.schedule!='normal' and not a.timing_verify:p.error('diagnostic schedule requires --timing-verify')
    if a.timing_verify and not a.timing:p.error('--timing-verify requires --timing')
    if a.frame_stats and not (a.timing or a.release):p.error('--frame-stats requires --timing or --release')
    if a.view_control and not a.release:p.error('--view-control requires --release')
    if a.timing or a.release:
        if a.iterations: p.error('timing fixture cannot also use the old delay tail')
        subprocess.run([sys.executable,str(ROOT/'tools/reconstruct.py'),'--release' if a.release else '--timing','--output',a.output]+(['--timing-verify'] if a.timing_verify else [])+(['--flight-verify'] if a.flight_verify else [])+(['--flight-control'] if a.flight_control else [])+(['--frame-stats'] if a.frame_stats else []),check=True)
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
    if a.timing_verify:
        symbols={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(out/'slave.lst').read_text(),re.M)}
        at=32+symbols['timing_verify_schedule']
        data[at:at+2]=struct.pack('>H',{'normal':0,'slow':10,'one-field':1}[a.schedule])
    if a.view_control:
        symbols={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(out/'slave.lst').read_text(),re.M)}
        for name in ('view_clear','view_compose'):
            at=32+symbols[name]+4
            assert data[at:at+2]==bytes.fromhex('6700')
            data[at:at+2]=bytes.fromhex('6000') # same-size unconditional native fallback
    slave.write_bytes(data)
    meta=json.loads((out/'build.json').read_text())
    meta.update(view_control=a.view_control,direct_flight=True,nav=a.nav,schedule=a.schedule,argument_immediate=0x156d,
                sha256=hashlib.sha256(data).hexdigest())
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n')

if __name__=='__main__': main()
