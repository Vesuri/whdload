#!/usr/bin/env python3
"""Read W3–W6 VERIFY twin counts from a retained capture, without emitting game bytes."""
import argparse, os, re, struct
from pathlib import Path
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
p.add_argument('--bits',type=lambda s:int(s,0),default=60)
p.add_argument('--all-variants',action='store_true')
p.add_argument('--require-current',action='store_true',help='require eight ray sites, CPU-safe flag reads and fixed-width clear coverage')
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
b=(a.capture/'code.bin').read_bytes();lst=(a.capture/'slave.lst').read_text(errors='replace')
r={n:lo for lo,hi,n,o in regions(b,a.base)}
def has(n):
    return bool(re.search(r'^'+n+r'\s+00:',lst,re.M))
def read(n,fmt):
    m=re.search(r'^'+n+r'\s+00:([0-9A-F]{8})\s*(?:EXP)?\s*$',lst,re.M)
    assert m, 'missing symbol '+n
    return struct.unpack_from('>'+fmt,b,r['slave']-a.base+int(m[1],16))
bits=read('_custom2','I')[0];verify=read('_custom5','I')[0]
if a.require_current:
    assert all(has(n) for n in ('_verify_ccr_patched','_verify_ccr_site_count','_w5_resume_7','_w6_clear_fallback','_w6_counts')),'capture is an older source revision'
if re.search(r'^_verify_ccr_patched\s+00:',lst,re.M):
    newer=bool(read('_lov_attnflags','I')[0]&1)
    sites=read('_verify_ccr_site_count','H')[0] if has('_verify_ccr_site_count') else 15
    assert read('_verify_ccr_patched','H')[0]==(sites if newer else 0),'flag-capture selection incomplete'
    ids=re.findall(r"^_verify_sr_(\d+)\s+00:",lst,re.M)
    assert len(ids)==sites,'flag-site table does not cover the capture symbols'
    for i in ids:
        assert read(f'_verify_sr_{i}','H')[0] in ((0x42e7,0x42c0) if newer else (0x40e7,0x40c0)),'incorrect flag-capture opcode'
    print('flag captures:', 'CCR (68010+)' if newer else 'SR (68000)')
else:
    print('flag captures: legacy SR verifier')
for bit,name,sym,fmt in [(2,'wall columns','_w3_cases','3I'),(3,'sprite columns','_w4_cases','3I'),(4,'ray reciprocals','_w5_tests','I'),(5,'chunky clear','_w6_counts' if has('_w6_counts') else '_w6_tests','3I' if has('_w6_counts') else 'I')]:
    if not a.bits&(1<<bit):continue
    assert bits&(1<<bit) and verify&(1<<(bit+2)),name+' twin was disabled'
    counts=read(sym,fmt)
    assert sum(counts)>0,name+' had no successful comparisons'
    if a.all_variants:assert all(counts),name+' has an untested variant'
    print(name+': '+', '.join(str(c) for c in counts)+' successful twins')
    if bit==4:
        expected=262140 if has('_w5_resume_7') else 131070
        assert read('_w5_units','I')[0]==expected,'reciprocal exhaustive test incomplete'
        print(f'  every nonzero 16-bit divisor tested with X clear/set: {expected} comparisons; '+('both register orders, eight sites' if expected==262140 else 'legacy two-site revision'))
