#!/usr/bin/env python3
"""Build pinned experimental OCS converter components; never modifies a slave."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from ocs_reconstruct import ROOT, new_output, require


def candidates(root=None):
    root = Path(root or os.environ.get('OCS_KALMS_ROOT') or
                Path(os.environ['AMIGA_SHARE'])/'kalms-c2p')
    result = []
    for line in (ROOT/'tools/manifest/ocs-c2p-candidates.tsv').read_text().splitlines():
        if not line or line.startswith('#'): continue
        name, digest, url = line.split('\t')
        raw = (root/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == digest,
                'changed Kalms input; preserved unchanged: '+name)
        result.append((name, digest, raw.decode()))
    require(len(result) == 2, 'expected two pinned candidates')
    return result


def source(inputs):
    # Upstream byte/word/plane shuffle is unchanged. A row adapter supplies
    # low-nibble colour values; full upstream sources remain derived tmp output.
    return (ROOT/'src/ocs_c2p.s').read_text()+'\n'+'\n'.join(x[2] for x in inputs)


def assemble(out, name, text):
    src = out/(name+'.s')
    src.write_text(text)
    cmd = [os.environ['VASM'], '-m68000', '-spaces', '-no-opt', '-Fbin',
           '-I'+os.environ['NDK'], '-L', str(out/(name+'.lst')),
           '-o', str(out/(name+'.bin')), str(src)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    require(result.returncode == 0, result.stdout+result.stderr)
    blob = (out/(name+'.bin')).read_bytes()
    symbols = {n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',
               (out/(name+'.lst')).read_text(), re.M)}
    return blob, symbols


def build(out, inputs=None):
    inputs = candidates() if inputs is None else inputs
    blob, symbols = assemble(out, 'converters', source(inputs))
    report = dict(experimental=True, installed=False, default='native QBlit',
                  inputs={name:digest for name,digest,_ in inputs},
                  cpu='68000', bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                  entries={key:symbols[key] for key in ('ocs_c2p_native','ocs_c2p_word','ocs_c2p_long')},
                  stack_reserve=512, source_stride='width', destination_stride='width/8',
                  completed=0, native_request=1, invalid=2)
    (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    return blob, symbols


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    inputs = candidates()  # reject changed inputs before making output
    out = new_output(a.output); out.mkdir(parents=True)
    build(out, inputs)
    print('Built experimental converters; native slave unchanged')


if __name__ == '__main__': main()
