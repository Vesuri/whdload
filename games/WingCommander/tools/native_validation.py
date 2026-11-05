"""Variant-selected state, memory and pixel contracts; no CD32-to-OCS fallback."""
from variants import get


def equal_bytes(a, b, size, label):
    if len(a) != size or len(b) != size:
        raise ValueError('truncated '+label)
    if a != b:
        first = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        raise ValueError(f'{label} differs at offset {first:#x}')


def state(variant, left, right):
    v = get(variant)
    if len(left) != len(v.HUNKS) or len(right) != len(v.HUNKS):
        raise ValueError('wrong hunk count')
    for n, (_, _, size) in enumerate(v.HUNKS):
        equal_bytes(left[n], right[n], size, f'{variant} hunk {n}')
    return sum(h[2] for h in v.HUNKS)


def dma_regions(regions, headers):
    """Every complete DMA region in actual MEMF_CHIP storage, with no aliases."""
    for start, end in regions:
        if start & 1 or not 0 < start < end or not any(
                attrs & 2 and lower <= start < end <= upper for attrs, lower, upper in headers):
            raise ValueError('DMA storage is not aligned Chip RAM')
    for i, (a, b) in enumerate(regions):
        if any(max(a, c) < min(b, d) for c, d in regions[i+1:]):
            raise ValueError('overlapping native DMA allocations')


def chunky_pixels(variant, source, width, height):
    v = get(variant)
    if width <= 0 or height <= 0 or len(source) != width*height:
        raise ValueError('invalid chunky extent')
    if v.BITMAP['colour'] == 'byte':
        return bytes(source)
    if v.BITMAP['colour'] != 'checkerboard-nibbles':
        raise ValueError('unsupported native colour layout')
    return bytes((value >> (4 if (i % width+i//width) % 2 == 0 else 0)) & 15
                 for i, value in enumerate(source))


def planar_pixels(variant, planes, width, height, row, plane, leading=None):
    v = get(variant)
    leading = v.BITMAP['leading_rows'] if leading is None else leading
    if width <= 0 or height <= 0 or width > row*8 or leading < 0 or (height+leading)*row > plane:
        raise ValueError('invalid planar extent')
    if len(planes) != plane*v.BITMAP['depth']:
        raise ValueError('truncated planar storage')
    return bytes(sum(((planes[n*plane+(y+leading)*row+x//8] >> (7-x%8)) & 1) << n
                     for n in range(v.BITMAP['depth']))
                 for y in range(height) for x in range(width))
