#!/usr/bin/env python3
"""Reject deliberately corrupt C4 ownership and pixel evidence, without edits."""
import argparse
import json
import struct
import ocs_memory_report
from pathlib import Path
from unittest.mock import patch
from ocs_memory_report import report
from ocs_reconstruct import new_output


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--build',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();root=Path(a.run);build=Path(a.build)
    report(root,build)
    m=json.loads((root/'result.json').read_text());b=json.loads((build/'build.json').read_text())
    original_bytes=Path.read_bytes;original_text=Path.read_text
    failures=[]
    for name,offset in (('lost source owner',m['a4']+0x10e6-0x200000),
                        ('wrong backend',m['slave']+b['symbols']['ocs_source_backend']-0x200000),
                        ('lost allocation registry',m['a4']-0x844-0x200000)):
        def read_bytes(path):
            raw=original_bytes(path)
            if path==root/'origin-fast.bin':
                raw=bytearray(raw);raw[offset:offset+4]=b'\xff'*4;raw=bytes(raw)
            return raw
        try:
            with patch.object(Path,'read_bytes',read_bytes):report(root,build)
        except ValueError:failures.append(name)
        else:raise ValueError('accepted corrupt evidence: '+name)
    def read_text(path,*args,**kwargs):
        raw=original_text(path,*args,**kwargs)
        if path==root/'asteroids-events.txt':
            rows=raw.splitlines()
            for n,line in enumerate(rows):
                if line.startswith('X '):
                    fields=line.split();fields[2]='1';rows[n]=' '.join(fields);break
            return '\n'.join(rows)+'\n'
        return raw
    try:
        with patch.object(Path,'read_text',read_text):report(root,build)
    except ValueError:failures.append('pixel mismatch')
    else:raise ValueError('accepted corrupt pixel evidence')
    if 'teardown' in m['checkpoints']:
        original_load=ocs_memory_report.barto.load
        code=(root/'name-h0.bin').read_bytes()
        old_plane=int.from_bytes(code[0x331c0:0x331c4],'big')
        def corrupt_dma(path):
            trace=original_load(path)
            if Path(path)==root/'teardown-screen.bin':
                raw=bytearray(trace.fields[1].dma)
                struct.pack_into('<H',raw,0,0x110)
                struct.pack_into('<I',raw,12,old_plane)
                struct.pack_into('<h',raw,29,6)
                trace.fields[1].dma=memoryview(raw)
            return trace
        try:
            with patch.object(ocs_memory_report.barto,'load',corrupt_dma):report(root,build)
        except ValueError:failures.append('stale DMA after exit')
        else:raise ValueError('accepted stale DMA')
        gfx=int.from_bytes(code[0x33518:0x3351c],'big')
        def wrong_copper(path):
            raw=original_bytes(path)
            if path==root/'teardown-fast.bin':
                raw=bytearray(raw);off=gfx+50-0x200000
                raw[off:off+4]=bytes(4);raw=bytes(raw)
            return raw
        try:
            with patch.object(Path,'read_bytes',wrong_copper):report(root,build)
        except ValueError:failures.append('unproved restored Copper owner')
        else:raise ValueError('accepted bad OS ownership')
    out=new_output(a.output);out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(dict(passed=True,rejected=failures),indent=2)+'\n')
    print(len(failures),'bad evidence controls rejected')

if __name__=='__main__':main()
