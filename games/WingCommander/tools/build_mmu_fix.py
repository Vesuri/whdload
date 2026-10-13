#!/usr/bin/env python3
"""Build a project-local FS-UAE with correct 040/060 MMU write cache attributes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'b70b1180b44ab25b97cd66466c70879897d8a362'
OLD = ('addr = atc_data_cache_write[idx2].phys | (addr & mmu_pagemask);\n'
       '\t\t\tmmu_cache_state = atc_data_cache_read[idx2].cache_state;')
NEW = OLD.replace('atc_data_cache_read', 'atc_data_cache_write')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='tmp/fsuae-mmu-fixed')
    p.add_argument('--ensure', action='store_true', help='reuse an intact normal build')
    p.add_argument('--audit', action='store_true', help='read-only CPU/DMA pixel and frontend screenshot observer')
    p.add_argument('--unfixed-control', action='store_true', help='audit the original bug; never use as the normal launcher')
    a = p.parse_args()
    if a.unfixed_control and not a.audit:
        p.error('--unfixed-control requires --audit')
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents:
        p.error('output must be below tmp/')
    if out.exists():
        if a.ensure and not a.audit and not a.unfixed_control:
            meta = json.loads((out/'mmu-fix.json').read_text())
            if meta['fixed'] and not meta['audit'] and sha(out/'fs-uae') == meta['sha256']:
                return
        raise ValueError('existing/changed output is preserved; choose a new directory')
    source = Path(os.environ['FSUAE_SOURCE'] if 'FSUAE_SOURCE' in os.environ
                  else os.environ['AMIGA_SHARE']+'/fs-uae-aprof-build/fs-uae')
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise ValueError('unsupported source revision')
    inputs = {}
    for line in (ROOT/'manifest/mmu-fix.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, expected = line.split()
        if sha(source/name) != expected:
            raise ValueError('changed source is preserved: '+name)
        inputs[name] = expected
    shutil.copytree(source, out, ignore=shutil.ignore_patterns('.git'))
    header = out/'src/include/cpummu.h'
    text = header.read_text()
    if text.count(OLD) != 6:
        raise ValueError('expected six ordinary/locked byte/word/long write paths')
    if not a.unfixed_control:
        header.write_text(text.replace(OLD, NEW))
    if a.audit:
        cpu = out/'src/newcpu.cpp'
        text = cpu.read_text().replace('#include "sysconfig.h"',
            '#include "sysconfig.h"\n#include "fsemu-screenshot.h"\nstatic void wc_visual_observe(uae_u32 pc);', 1)
        start = text.index('static void m68k_run_mmu040 (void)')
        end = text.index('static void m68k_run_mmu030', start)
        part = text[start:end]
        anchor = 'regs.instruction_pc = m68k_getpc ();'
        assert part.count(anchor) == 1
        part = part.replace(anchor, anchor+'\n                wc_visual_observe(regs.instruction_pc);')
        text = text[:start]+part+text[end:]
        anchor = 'static uae_u32 read_dcache040(uae_u32 addr'
        assert text.count(anchor) == 1
        text = text.replace(anchor, '#include "wc_visual_audit.inc"\n\n'+anchor)
        cpu.write_text(text)
        shutil.copyfile(ROOT/'tools/visual_audit.inc', out/'src/wc_visual_audit.inc')
    env = dict(os.environ, TMPDIR=str(out))
    with (out/'build.log').open('w') as log:
        subprocess.run(['/usr/bin/make', '-j4', 'fs-uae'], cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    meta = dict(revision=revision, inputs=inputs, fixed=not a.unfixed_control,
                audit=a.audit, sha256=sha(out/'fs-uae'))
    if a.audit:
        meta['audit_sha256'] = sha(ROOT/'tools/visual_audit.inc')
    (out/'mmu-fix.json').write_text(json.dumps(meta, indent=2)+'\n')
    print('Built '+str(out.relative_to(ROOT))+'/fs-uae ('+meta['sha256']+')')


if __name__ == '__main__':
    main()
