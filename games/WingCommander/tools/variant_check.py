#!/usr/bin/env python3
"""P13B1 byte-preserving builds, maps, explicit selection and live-layout regression.

Before artifacts must be built from the parent revision, before the refactor.
Memory inputs are retained native snapshots, not performance measurements.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import _amigaxdev
from amitools.binfmt.hunk.HunkReader import HunkReader
from variants import get, assembly_definitions, timing_hooks
from variant_runtime import segment_chain
from timing_source import source as timing_source
from render_source import source as render_source

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def reject(action):
    try:
        action()
    except (ValueError, KeyError):
        return
    raise ValueError('negative control was accepted')


def identical(a, b):
    require(a == b, 'binary changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-prefix', required=True, type=Path)
    p.add_argument('--after-prefix', required=True, type=Path)
    p.add_argument('--cd32-memory', required=True, type=Path)
    p.add_argument('--ocs-memory', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    out = a.output.resolve()
    require((ROOT/'tmp').resolve() in out.parents and not out.exists(), 'new tmp output required')
    out.mkdir(parents=True)
    builds = {}
    for mode in ('release', 'timing', 'render', 'native'):
        before = Path(str(a.before_prefix)+'-'+mode)/'WingCommanderCD32.Slave'
        after = Path(str(a.after_prefix)+'-'+mode)/'WingCommanderCD32.Slave'
        raw, built = before.read_bytes(), after.read_bytes()
        identical(raw, built)
        reject(lambda: identical(raw, bytes([built[0]^1])+built[1:]))
        reject(lambda: identical(raw, built[:-1]))
        builds[mode] = dict(bytes=len(built), sha256=hashlib.sha256(built).hexdigest())
    maps, layouts = {}, {}
    for name, memory_path in (('cd32', a.cd32_memory), ('ocs', a.ocs_memory)):
        v = get(name)
        game = (ROOT/v.GAME).read_bytes()
        require(hashlib.sha256(game).hexdigest() == v.GAME_SHA, 'game identity mismatch')
        reader = HunkReader()
        require(reader.read_file(str(ROOT/v.GAME)) == 0, 'cannot read HUNK')
        actual = [(h.get('data_file_offset'), len(h.get('data', b'')), h['size'])
                  for h in reader.hunks if h['type_name'] in ('HUNK_CODE','HUNK_DATA','HUNK_BSS')]
        # HunkReader size describes stored payload; allocation table includes DATA tail.
        actual = [(off, size, reader.hunks[0]['hunks'][i]['size']) for i,(off,size,_) in enumerate(actual)]
        require(tuple(actual) == v.HUNKS, 'hunk map disagrees with native file')
        for offset in v.NATIVE.values():
            require(0 <= offset < v.HUNKS[0][1] and offset % 2 == 0, 'invalid native entry')
        for offset in v.A4.values():
            require(0 <= v.A4_BASE+offset < v.HUNKS[1][2], 'A4 field outside DATA')
        asm = out/(name+'.s')
        asm.write_text(assembly_definitions(v)+'probe: rts\n')
        binary = out/(name+'.bin')
        subprocess.run([os.environ['VASM'], '-m'+v.CPU, '-spaces', '-no-opt', '-Fbin',
                        '-o', str(binary), str(asm)], check=True, capture_output=True)
        require(binary.read_bytes() == bytes.fromhex('4e75'), 'definitions emitted runtime bytes')
        memory = memory_path.read_bytes()
        runtime = importlib.import_module(name+'_runtime')
        layout = runtime.locate(memory)
        layouts[name] = layout
        sizes = tuple(h[2] for h in v.HUNKS)
        require(segment_chain(memory, runtime.BASE, layout['hunks'][0], sizes) == layout['hunks'], 'segment chain mismatch')
        bad = bytearray(memory)
        off = layout['hunks'][0]-runtime.BASE
        bad[off-8] ^= 1
        reject(lambda: runtime.locate(bad))
        bad = bytearray(memory)
        last = layout['hunks'][-1]-runtime.BASE
        struct.pack_into('>I', bad, last-4, 1)
        reject(lambda: runtime.locate(bad))
        other = importlib.import_module(('ocs' if name=='cd32' else 'cd32')+'_runtime')
        reject(lambda: other.locate(memory))
        maps[name] = dict(hunks_verified=True, equates_emit_zero_bytes=True,
                          wrong_allocation_rejected=True, nonterminal_chain_rejected=True,
                          opposite_variant_rejected=True)
    # Change a consumed definition, rebuild, and prove the binary gate notices it.
    # The repository map is never edited; the mutation lives in this process only.
    from reconstruct import cd32_main
    altered = SimpleNamespace(**vars(get('cd32')))
    altered.A4 = dict(altered.A4, field_clock=altered.A4['field_clock']-2)
    with patch('variants.cd32', altered):
        cd32_main(['--release', '--output', str(out/'changed-map')])
    native = (Path(str(a.after_prefix)+'-release')/'WingCommanderCD32.Slave').read_bytes()
    changed = (out/'changed-map/WingCommanderCD32.Slave').read_bytes()
    reject(lambda: identical(native, changed))
    ocs = get('ocs')
    original = (ROOT/ocs.SLAVE).read_bytes()
    identical(original, (Path(str(a.after_prefix)+'-ocs')/'WingCommander.Slave').read_bytes())
    require(hashlib.sha256(original).hexdigest() == ocs.SLAVE_SHA, 'OCS input changed')
    reject(lambda: get('unknown'))
    reject(lambda: timing_hooks(ocs))
    reject(lambda: timing_source(ROOT, variant='ocs'))
    reject(lambda: render_source(ROOT, variant='ocs'))
    commands = [
        ['reconstruct.py', '--output', str(out/'missing-variant')],
        ['reconstruct.py', '--variant', 'ocs', '--release', '--output', str(out/'unsupported')],
        ['reconstruct.py', '--variant', 'cd32', '--input', ocs.SLAVE, '--output', str(out/'wrong-input')],
        ['analyze.py', 'definitions'],
        ['analyze.py', '--variant', 'unknown', 'definitions'],
    ]
    for command in commands:
        result = subprocess.run([sys.executable, str(ROOT/'tools'/command[0]), *command[1:]], capture_output=True)
        require(result.returncode != 0, 'invalid CLI accepted')
    require(not any((out/name).exists() for name in ('missing-variant','unsupported','wrong-input')), 'rejected build wrote output')
    report = dict(passed=True, byte_identical_cd32=builds, byte_identical_ocs=True,
                  maps=maps, layouts=layouts, negative_cli_cases=len(commands),
                  changed_field_map_rejected=True, no_emulator_run=True)
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
