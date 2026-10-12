#!/usr/bin/env python3
"""Build the established debugger-native key route on a local shared-build copy.
Never modifies the shared installation. Requires its configured aprof build tree.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    source = Path(os.environ.get('FSUAE_SOURCE', os.environ['AMIGA_SHARE']+'/fs-uae-aprof-build/fs-uae'))
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output directory below tmp/')
    revision = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if revision != 'b70b1180b44ab25b97cd66466c70879897d8a362':
        raise ValueError('unsupported shared source revision')
    for row in (ROOT/'manifest/debugger.tsv').read_text().splitlines():
        if not row or row.startswith('#'): continue
        name, digest = row.split('\t')
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != digest:
            raise ValueError('shared build source differs: '+name)
    shutil.copytree(source, out, ignore=shutil.ignore_patterns('.git'))
    p = out/'src/keybuf.cpp'
    s = p.read_text()
    # Same native keyboard queue as the 4D Sports Driving debugger route.
    s += '''\n// Explicit debugger events must survive frontend focus-release suppression.
int record_key_debug(int kc) {
    ignore_next_release = false;
    return record_key_direct(kc);
}
'''
    p.write_text(s)
    p = out/'src/barto_gdbserver.cpp'
    s = p.read_text().replace('#include "sysconfig.h"', '#include "sysconfig.h"\nextern int record_key_debug(int);', 1)
    anchor = '} else if(cmd == "aprof start") {'
    assert s.count(anchor) == 1
    s = s.replace(anchor, '''} else if(cmd == "inputcaps") {
        response += to_hex("key-raw-v1");
    } else if(cmd.substr(0, 4) == "key ") {
        unsigned key = 0; int pressed = -1; char extra;
        if(sscanf(cmd.c_str(), "key %x %d %c", &key, &pressed, &extra) == 2
           && key < 0x80 && (pressed == 0 || pressed == 1)) {
            unsigned raw = key | (pressed ? 0 : 0x80);
            response += record_key_debug(((raw << 1) | (raw >> 7)) & 0xff) ? "OK" : "E02";
        } else response += "E01";
    '''+anchor)
    p.write_text(s)
    # Existing configured dependencies and objects are shared-build inputs; make
    # recompiles both touched translation units and links a new local binary.
    env = dict(os.environ, TMPDIR=str(out))
    subprocess.run(['/usr/bin/make','-j4','fs-uae'],cwd=out,env=env,check=True)
    subprocess.run([str(out/'fs-uae'),'--version'],check=True)
    print('local debugger:',out.relative_to(ROOT)/'fs-uae')

if __name__ == '__main__': main()
