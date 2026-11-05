"""Shared DOS segment traversal; variant locators retain independent identity guards."""
import struct


def segment_chain(memory, base, address, sizes):
    hunks = []
    for size in sizes:
        off = address - base
        if not 8 <= off <= len(memory) - size:
            raise ValueError('segment outside Fast RAM snapshot')
        allocated, following = struct.unpack_from('>II', memory, off-8)
        if allocated != size + 8:
            raise ValueError('not a DOS segment allocation')
        hunks.append(address)
        address = following * 4 + 4
    if following:
        raise ValueError('unterminated segment chain')
    return hunks
