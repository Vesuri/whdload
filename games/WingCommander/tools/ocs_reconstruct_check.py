#!/usr/bin/env python3
"""Static P13A1 identity, preservation and deliberate-failure gate; no emulator."""
import argparse
import json
import subprocess
import sys
from unittest.mock import patch

import ocs_reconstruct as ocs


def rejected(action, message):
    try:
        action()
    except ValueError as error:
        ocs.require(message in str(error), f'wrong rejection: {error}')
    else:
        raise ValueError('negative control was accepted: ' + message)


def crc_suffix(prefix, target):
    # Two appended bytes can produce each CRC16; do not recompute the full file
    # for each trial. This creates a real CRC collision, not a mocked CRC check.
    initial = ocs.crc16(prefix)
    for value in range(65536):
        suffix = value.to_bytes(2, 'big')
        crc = initial
        for byte in suffix:
            crc ^= byte
            for _ in range(8):
                crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
        if crc == target:
            return prefix + suffix
    raise ValueError('CRC suffix not found')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = ocs.new_output(args.output)
    original_root = ocs.ROOT / 'tmp/originals/ocs/WingCommander'
    before = {p.relative_to(original_root): ocs.sha(p.read_bytes())
              for p in original_root.rglob('*') if p.is_file()}
    slave = (original_root / 'WingCommander.Slave').read_bytes()
    game = (original_root / 'data/Wing.english').read_bytes()
    ocs.require(ocs.sha(slave) == ocs.SLAVE_SHA, 'reference slave changed')
    ocs.guard_game(game)
    out.mkdir(parents=True)
    first = ocs.build(out / 'first', slave, game)
    second = ocs.build(out / 'second', slave, game)
    ocs.require(first == second, 'repeat reports differ')
    for name in ('WingCommanderOCS.s', 'payload.bin', 'WingCommander.Slave', 'report.json'):
        ocs.require((out / 'first' / name).read_bytes() == (out / 'second' / name).read_bytes(),
                    'repeat output differs: ' + name)
    checks = ['two byte-identical base-ISA builds']
    # Test the public CLI as well as individual guards. Every fixture stays here.
    def cli_reject(label, data, option, expected):
        fixture = out / (label + '.input')
        fixture.write_bytes(data)
        destination = out / (label + '-build')
        proc = subprocess.run([sys.executable, str(ocs.ROOT / 'tools/ocs_reconstruct.py'),
                               '--output', str(destination), option, str(fixture)],
                              capture_output=True, text=True)
        ocs.require(proc.returncode != 0 and expected in proc.stderr, label + ' not rejected')
        ocs.require(not destination.exists() and fixture.read_bytes() == data,
                    label + ' modified input or created build output')
        checks.append(label)
    changed = bytearray(slave)
    changed[0x20 + 0x10f4] ^= 1
    cli_reject('changed-slave', changed, '--input', 'unsupported/changed OCS slave')
    cli_reject('truncated-slave', slave[:-1], '--input', 'unsupported/changed OCS slave')
    cli_reject('truncated-game', game[:-1], '--game', 'unsupported/changed OCS game')
    cd32 = (ocs.ROOT / 'tmp/originals/cd32/WingCommanderCD32/data/wing.english').read_bytes()
    cli_reject('wrong-variant', cd32, '--game', 'unsupported/changed OCS game')
    changed = bytearray(game)
    changed[0x2c + 0x26a3c] ^= 1
    collision = crc_suffix(bytes(changed[:-2]), 0x00e8)
    ocs.require(ocs.crc16(collision) == 0x00e8 and ocs.sha(collision) != ocs.GAME_SHA,
                'collision control invalid')
    cli_reject('same-crc-altered-game', collision, '--game', 'unsupported/changed OCS game')
    # The other stock selectors are decoded, but cannot certify absent revisions.
    for crc in (0x116d, 0x262d):
        fixture = crc_suffix(b'unsupported revision fixture', crc)
        ocs.require(ocs.crc16(fixture) == crc, 'invalid revision fixture')
        cli_reject(f'unverified-crc-{crc:04x}', fixture, '--game', 'unsupported/changed OCS game')
    for site in first['displaced_sites']:
        changed = bytearray(game)
        changed[int(site['file_offset'], 16)] ^= 1
        rejected(lambda: ocs.guard_sites(changed), 'displaced bytes differ')
    checks.append('all eight displaced-site guards reject mutations independently')
    code = slave[0x20:-4]
    for pos, _, _ in ocs.SELECTORS:
        for relative, message in ((0, 'instruction changed'), (3, 'target changed'),
                                  (7, 'instruction changed'), (8, 'branch changed' if pos != 0x1170 else 'abort changed')):
            changed = bytearray(code)
            changed[pos + relative] ^= 1
            rejected(lambda: ocs.revision_lists(changed), message)
    checks.append('12 selector opcode/CRC/target/branch mutations rejected')
    source, count = ocs.assembly(code)
    # Deliberately damage a real assembled instruction. The identity gate must
    # reject the result and must not produce a supposedly usable slave.
    broken = source.replace('moveq #$ff, d0', 'moveq #0, d0', 1)
    if broken == source:
        broken = source.replace('moveq #-1, d0', 'moveq #0, d0', 1)
    ocs.require(broken != source, 'assembly sabotage did not change source')
    with patch.object(ocs, 'assembly', return_value=(broken, count)):
        rejected(lambda: ocs.build(out / 'bad-assembly', slave, game), 'payload differs')
    ocs.require(not (out / 'bad-assembly/WingCommander.Slave').exists(), 'bad slave published')
    checks.append('assembled instruction sabotage rejected')
    rejected(lambda: ocs.new_output(out / 'first'), 'output exists')
    rejected(lambda: ocs.new_output(ocs.ROOT / 'docs/p13a1-forbidden'), 'below tmp/')
    (out / 'outside-link').symlink_to(ocs.ROOT / 'docs', target_is_directory=True)
    rejected(lambda: ocs.new_output(out / 'outside-link/p13a1-forbidden'), 'below tmp/')
    checks.append('existing, outside-tmp and symlink-escape outputs rejected')
    after = {p.relative_to(original_root): ocs.sha(p.read_bytes())
             for p in original_root.rglob('*') if p.is_file()}
    ocs.require(before == after, 'original OCS tree changed')
    checks.append('original OCS tree preserved')
    report = {'passed': True, 'checks': checks, 'slave_sha256': first['sha256'],
              'emulator_runs': 0}
    (out / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
