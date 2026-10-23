#!/usr/bin/env python3
"""B4: compare all optional hook ranges with the relocated, pinned original.

Ranges come from PERF_RANGE comments immediately before PL_PS, PL_NOP or PL_R hooks. Baseline loader
patches are explicitly delimited separately. Unknown optional patch forms fail closed;
extend the audit alongside any future patch type. No original bytes are stored here.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from slave_inputs import ROOT, verify
from race_profile import GAME, image, locate, game_hunks

SOURCE = ROOT/'whdload/F1GP.s'
PATTERN = re.compile(r'; PERF_RANGE h(\d+):([0-9a-fA-F]+) (\d+) custom=([1-5]) bit=(\d+) variant=(\d+)$')


def ranges(source):
    result, baseline, pending, gate = [], False, None, None
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if line.startswith('; BASELINE_PATCHES_BEGIN'):
            if baseline:
                raise ValueError('nested baseline block')
            baseline = True
        elif line == '; BASELINE_PATCHES_END':
            if not baseline:
                raise ValueError('unmatched baseline end')
            baseline = False
        elif 'PERF_RANGE' in line:
            match = PATTERN.fullmatch(line)
            if not match or pending or baseline:
                raise ValueError(f'invalid range at line {number}')
            h, off, size, custom, bit, variant = match.groups()
            pending = dict(hunk=int(h), offset=int(off,16), size=int(size),
                           custom=int(custom), bit=int(bit), variant=int(variant))
            if gate != (pending['custom'],pending['bit']) or pending['bit'] > 31:
                raise ValueError('range not inside its declared CUSTOM bit gate')
        elif line.startswith('PL_IFC'):
            match = re.fullmatch(r'PL_IFC([1-5])X (\d+)', line)
            if not match or gate:
                raise ValueError('unsupported or nested gate')
            gate = tuple(map(int,match.groups()))
        elif line == 'PL_ENDIF':
            if not gate or pending:
                raise ValueError('unmatched gate')
            gate = None
        elif line.startswith('PL_') and not baseline:
            if line in ('PL_START','PL_END'):
                continue
            call = re.fullmatch(r'PL_PS \$([0-9a-fA-F]+),\w+', line)
            nop = re.fullmatch(r'PL_NOP \$([0-9a-fA-F]+),(\d+)', line)
            ret = re.fullmatch(r'PL_R \$([0-9a-fA-F]+)', line)
            match = call or nop or ret
            size = 6 if call else int(nop[2]) if nop else 2
            # Supported hooks are in hunk 0: PatchSeg's flat offset is identical.
            if (not pending or not match or pending['hunk'] != 0
                    or size < 2 or size % 2 or pending['size'] != size
                    or int(match[1],16) != pending['offset']):
                raise ValueError(f'unannotated/unsupported hook at line {number}')
            result.append(pending)
            pending = None
        elif pending:
            raise ValueError('range must immediately precede its hook')
    if pending or baseline or gate or not result:
        raise ValueError('incomplete or empty range declarations')
    options = {tuple(map(int, pair)) for pair in re.findall(r'C([1-5]):X:[^;\n]+:(\d+);', source)}
    if any((r['custom'], r['bit']) not in options for r in result):
        raise ValueError('hook bit missing from slv_config')
    occupied = set()
    for r in result:
        for off in range(r['offset'],r['offset']+r['size']):
            key = r['variant'],r['hunk'],off
            if key in occupied:
                raise ValueError('overlapping hook ranges')
            occupied.add(key)
    return result


def relocated_original(bases):
    """Reconstruct HUNK_CODE/DATA relocations, including references to BSS hunks."""
    data = Path(GAME).read_bytes()
    u = lambda p: struct.unpack_from('>I',data,p)[0]
    if u(0) != 1011 or u(4) != 0 or u(12) != 0:
        raise ValueError('unsupported HUNK header')
    p, h, loaded = 20+4*(u(16)+1), 0, {}
    while p < len(data):
        kind = u(p)&0x3fffffff; p += 4
        if kind in (1001,1002):
            n=u(p)*4; p+=4
            loaded[h]=bytearray(data[p:p+n]); p+=n
        elif kind == 1003:
            loaded[h]=bytearray(u(p)*4); p+=4
        elif kind == 1004:
            while u(p):
                count,target=u(p),u(p+4); p+=8
                for _ in range(count):
                    off=u(p); p+=4
                    value=struct.unpack_from('>I',loaded[h],off)[0]+bases[target]
                    struct.pack_into('>I',loaded[h],off,value)
            p+=4
        elif kind == 1010:
            h+=1
        else:
            raise ValueError(f'unsupported HUNK record {kind}')
    return loaded


def check(capture, source=SOURCE):
    verify()
    capture=Path(capture).resolve()
    if not capture.is_relative_to(ROOT/'tmp'):
        raise ValueError('capture must be in tmp/')
    meta=json.loads((capture/'meta.json').read_text())
    declared=ranges(source.read_text())
    if hashlib.sha256((capture/'slave.bin').read_bytes()).hexdigest() != meta['slave_sha256']:
        raise ValueError('captured slave differs from metadata')
    if meta['game_inputs'] != json.loads((ROOT/'manifest/game-inputs.json').read_text()):
        raise ValueError('capture input pins differ')
    if meta['source_sha256'] != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('capture source is stale')
    if meta['custom'] != [0]*5:
        raise ValueError('all CUSTOM values must be zero for the disabled gate')
    mem=image((capture/'chip.bin').read_bytes(),(capture/'fast.bin').read_bytes(),b'')
    actual=locate(mem,game_hunks())
    next_hunk=lambda b: struct.unpack_from('>I',mem,b-4)[0]*4+4
    bases=[actual[0][0],next_hunk(actual[0][0]),actual[2][0],next_hunk(actual[2][0])]
    if bases != meta['hunk_bases']:
        raise ValueError('capture layout differs from metadata')
    original=relocated_original(bases)
    selected=[r for r in declared if r['variant']==Path(GAME).stat().st_size]
    if not selected:
        raise ValueError('no ranges for this game variant')
    rows=[]
    for r in selected:
        h,o,n=r['hunk'],r['offset'],r['size']
        want=original[h][o:o+n]; got=mem[bases[h]+o:bases[h]+o+n]
        rows.append(dict(**r, matches=len(want)==len(got)==n and got==want))
    result=dict(status='PASS' if all(r['matches'] for r in rows) else 'FAIL',
                ranges=rows, hunk_bases=bases, slave_sha256=meta['slave_sha256'])
    return result


if __name__=='__main__':
    try:
        result=check(sys.argv[1])
        (Path(sys.argv[1])/'disabled.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        sys.exit(0 if result['status']=='PASS' else 1)
    except (ValueError,KeyError,OSError,IndexError) as error:
        print(f'FAIL: {error}',file=sys.stderr)
        sys.exit(1)
