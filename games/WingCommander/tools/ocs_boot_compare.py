#!/usr/bin/env python3
"""P13A3 strict state/picture comparison, no ignored bytes or pixels."""
import argparse
import json
import struct
from pathlib import Path
from PIL import Image
from ocs_runtime import SIZES, locate
from native_validation import equal_bytes, dma_regions, chunky_pixels, planar_pixels


def memory_contract(root, label):
    chip = (root/(label+'-chip.bin')).read_bytes()
    fast = (root/(label+'-fast.bin')).read_bytes()
    code = (root/(label+'-h0.bin')).read_bytes()
    def read(address, count):
        if 0 <= address <= len(chip)-count:
            return chip[address:address+count]
        offset = address-0x200000
        if 0 <= offset <= len(fast)-count:
            return fast[offset:offset+count]
        raise ValueError('snapshot address outside declared RAM')
    def integer(address, count=4):
        return int.from_bytes(read(address, count), 'big')
    # ExecBase -> MemList -> MemHeader; attributes distinguish true Fast
    # from merely PUBLIC allocation. Each list is bounded and must terminate.
    header = integer(integer(4)+322)
    headers = []
    for _ in range(16):
        following = integer(header)
        if not following:
            break
        attrs = integer(header+14, 2)
        lower, upper = integer(header+20), integer(header+24)
        if not lower < upper:
            raise ValueError('invalid OS memory header')
        headers.append((attrs, lower, upper))
        header = following
    else:
        raise ValueError('unterminated OS memory list')
    if not any(attrs & 4 and 0x200000 <= lower < upper <= 0x600000
               for attrs, lower, upper in headers):
        raise ValueError('no true Fast RAM in native OS list')
    if not any(attrs & 2 and upper == 0x80000 for attrs, lower, upper in headers):
        raise ValueError('native Chip memory limit differs')
    layout = locate(fast)
    if not all(any(attrs & 4 and lower <= base and base+size <= upper
                   for attrs, lower, upper in headers)
               for base, size in zip(layout['hunks'], SIZES)):
        raise ValueError('game segment outside true Fast allocation')
    state = code[0x331b8:0x331b8+36]
    size, workspace, display0, display1 = struct.unpack_from('>IIII', state)
    width, height = struct.unpack_from('>HH', state, 16)
    row, plane = struct.unpack_from('>HH', state, 24)
    source = int.from_bytes(code[0x324b0:0x324b4], 'big')
    if row != (width+15)//16*2 or plane != row*(height+2) or size != 4*plane:
        raise ValueError('native plane geometry differs')
    regions = [(p, p+size) for p in (workspace, display0, display1)]
    regions.append((source, source+width*height))
    dma_regions(regions, headers)
    return dict(width=width, height=height, memory_attributes=[h[0] for h in headers],
                chip_dma_regions=len(regions), planes=4)


def pixels(root):
    """Independent scalar packing at the quiescent name-input endpoint."""
    code = (root/'name-h0.bin').read_bytes()
    chip = (root/'name-chip.bin').read_bytes()
    if code[0x3291a:0x3291d] != bytes(3):
        raise ValueError('name conversion is still pending')
    state = code[0x331b8:0x331b8+36]
    width, height = struct.unpack_from('>HH', state, 16)
    row, plane = struct.unpack_from('>HH', state, 24)
    submitted = int.from_bytes(state[32:34], 'big')
    if submitted not in (0, 1):
        raise ValueError('invalid submitted display index')
    base = int.from_bytes(state[8+4*submitted:12+4*submitted], 'big')
    source = int.from_bytes(code[0x324b0:0x324b4], 'big')
    expected, actual, plain, low = (bytearray() for _ in range(4))
    edge = {(1, 1), (3, 1), (9, 1), (11, 1)}
    source_pixels = chunky_pixels('ocs', chip[source:source+width*height], width, height)
    plane_pixels = planar_pixels('ocs', chip[base:base+4*plane], width, height-1, row, plane)
    for y in range(height-1):
        for x in range(width):
            packed = chip[source+y*width+x]
            colour = source_pixels[y*width+x]
            plain.append(colour)
            low.append(0 if (x, y) in edge else packed & 15)
            expected.append(0 if (x, y) in edge else colour)
            actual.append(plane_pixels[y*width+x])
    equal_bytes(actual, expected, width*(height-1), 'published name pixels')
    differences = [(i % width, i // width) for i, (a, b) in enumerate(zip(actual, plain)) if a != b]
    if set(differences) != edge:
        raise ValueError('live edge fixture does not distinguish the four model pixels')
    if actual == low:
        raise ValueError('fixture does not reject low-nibble-only packing')
    return dict(pixels=len(actual), colours=len(set(actual)), exact=True,
                confirmed_black_edge_pixels=sorted(edge), low_nibble_only_rejected=True)


def compare(a, b):
    ma, mb = [json.loads((p/'result.json').read_text()) for p in (a, b)]
    for field in ('machine', 'warp', 'variant', 'fsuae_sha256', 'hunks', 'a4',
                  'actions', 'checkpoints', 'whd_args', 'effective', 'slave_sha256'):
        if ma[field] != mb[field]:
            raise ValueError('different run contract: '+field)
    if ma['machine'] != 'a500-ocs-512k-chip-4m-fast' or ma['warp'] or ma['whd_args']:
        raise ValueError('not the nominated native A500 gate')
    if ma['variant'] != 'ocs' or ma['checkpoints'] != ['origin', 'title', 'credits', 'menu', 'simulator', 'name']:
        raise ValueError('incomplete OCS route')
    results = {}
    for label in ma['checkpoints']:
        for n, size in enumerate(SIZES):
            equal_bytes(*[(p/f'{label}-h{n}.bin').read_bytes() for p in (a, b)], size, f'{label} h{n}')
        equal_bytes(*[(p/f'{label}-chip.bin').read_bytes() for p in (a, b)], 0x80000, label+' Chip RAM')
        images = [Image.open(p/(label+'.png')).convert('RGB') for p in (a, b)]
        if images[0].size != images[1].size:
            raise ValueError('different picture dimensions')
        equal_bytes(*[im.tobytes() for im in images], images[0].width*images[0].height*3, label+' RGB picture')
        memory = memory_contract(a, label)
        if memory_contract(b, label) != memory:
            raise ValueError('different native memory contracts')
        results[label] = dict(memory=memory, hunk_bytes=sum(SIZES), chip_bytes=0x80000,
                              pixels=images[0].width*images[0].height, differences=0)
    # Sabotage the actual strict comparator, including its length guard.
    for bad in (b'\x00\x02', b'\x00'):
        try:
            equal_bytes(b'\x00\x01', bad, 2, 'negative control')
        except ValueError:
            pass
        else:
            raise AssertionError('comparison accepted corrupt/truncated data')
    pixel_result = pixels(a)
    if pixels(b) != pixel_result:
        raise ValueError('different live pixel contracts')
    return dict(passed=True, checkpoints=results, native_pixels=pixel_result, negative_controls=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('reconstructed', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.original, args.reconstructed), indent=2))
