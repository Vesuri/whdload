#!/usr/bin/env python3
"""Static OCS inventory from pinned inputs; never boots or modifies an install."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from cd32_static import ROOT, crc16, inventory, require, sha
from amigaxdev.disasm import dis
from amigaxdev.patchlist import decode
from amitools.binfmt.hunk.HunkReader import HunkReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    require((ROOT / 'tmp').resolve() in out.parents, 'output must be below tmp/')
    require(not out.exists(), 'output exists; nothing overwritten')
    from archives import verified
    archives = {variant: verified(variant) for variant in ('ocs', 'installer')}
    out.mkdir(parents=True)
    for variant, archive in archives.items():
        dest = out / variant
        dest.mkdir()
        subprocess.run(['lha', 'xq', str(archive)], cwd=dest, check=True)
    game = out / 'ocs/WingCommander'
    reference = ROOT / 'tmp/game/WingCommander'
    fresh_files = {p.relative_to(game): sha(p.read_bytes()) for p in game.rglob('*') if p.is_file()}
    reference_files = {p.relative_to(reference): sha(p.read_bytes()) for p in reference.rglob('*') if p.is_file()}
    require(fresh_files == reference_files, 'reference tree differs; preserved unchanged')
    slave = game / 'WingCommander.Slave'
    require(slave.read_bytes() == (out / 'installer/WingCommanderHD/WingCommanderECS.slave').read_bytes(),
            'installer slave differs')
    require(crc16((game / 'data/Wing.english').read_bytes()) == 0x00e8,
            'unexpected English revision')
    reports = []
    relocations = {}
    for path in [slave] + sorted((game / 'data').glob('Wing.*')):
        report, _ = inventory(path, out, variant="ocs")
        reports.append(report)
        reader = HunkReader()
        require(reader.read_file(str(path)) == 0, reader.error_string)
        relocations[path.name] = [
            {'record': index, 'targets': record['reloc']}
            for index, record in enumerate(reader.hunks) if 'reloc' in record]
    code = (out / 'WingCommander.Slave.h0.bin').read_bytes()
    patches = {}
    for offset in (0x12bc, 0x1302, 0x1348):
        entries = [{'offset': address, 'command': command, 'argument': argument}
                   for address, command, argument in decode(code, offset)]
        require(len(entries) == 9 and entries[-1]['command'] == 'END',
                'unexpected revision patch list')
        patches[f'{offset:04x}'] = entries
    (out / 'patches.json').write_text(json.dumps(patches, indent=2) + '\n')
    (out / 'relocations.json').write_text(json.dumps(relocations, indent=2) + '\n')
    (out / 'inventory.json').write_text(json.dumps(reports, indent=2) + '\n')
    (out / 'files.json').write_text(json.dumps({str(k): v for k, v in sorted(fresh_files.items())}, indent=2) + '\n')
    print(json.dumps([{k: r[k] for k in ('name', 'size', 'sha256', 'crc16', 'hunks')} for r in reports], indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
