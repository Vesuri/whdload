#!/usr/bin/env python3
"""OCS native-routine semantics with a functional blitter, never a timing model.
Execute pinned original instructions; compare against independent pixel packing.
No ROM, WHDLoad, OS boot, renderer replacement or performance claim.
"""
import argparse
import ctypes as C
import json
import random
import struct
from ocs_reconstruct import ROOT, GAME_SHA, new_output, require, sha
from cd32_static import HunkReader
from c2p_check import u, ck, P, I, Q, Z

u.uc_emu_stop.argtypes = [P]
u.uc_emu_stop.restype = I

CODE, DATA, BSS, STARTUP = 0x100000, 0x140000, 0x150000, 0x160000
STACK, STOP, CUSTOM = 0x1f0000, 0x1000, 0xdff000
SOURCE, PLANES, WORK, OTHER = 0x30000, 0x50000, 0x60000, 0x70000
SURFACE, DESC, DESC2, NODE, FLAG = 0x180000, 0x181000, 0x182000, 0x183000, 0x183100


def word(value):
    return struct.pack('>H', value & 65535)


def long(value):
    return struct.pack('>I', value & 0xffffffff)


class Native:
    def __init__(self, game, model=1):
        require(sha(game.read_bytes()) == GAME_SHA, 'unsupported OCS executable')
        self.h = P()
        ck(u.uc_open(7, 1 << 30, C.byref(self.h)))
        ck(u.uc_ctl(self.h, 7 | (1 << 26) | (1 << 30), I(model)))  # M68000 by default
        ck(u.uc_mem_map(self.h, 0, 0x1000000, 7))
        reader = HunkReader()
        require(reader.read_file(str(game)) == 0, reader.error_string)
        bases = (CODE, DATA, BSS, STARTUP)
        index = -1
        for record in reader.hunks:
            if record['type_name'] in ('HUNK_CODE', 'HUNK_DATA', 'HUNK_BSS'):
                index += 1
                if 'data' in record:
                    self.write(bases[index], record['data'])
            if 'reloc' in record:
                for target, offsets in record['reloc'].items():
                    for offset in offsets:
                        address = bases[index] + offset
                        self.write(address, long(self.get(address, 4) + bases[target]))
        for current, following in zip(bases, bases[1:]):
            self.write(current-4, long((following-4)//4))
        self.write(bases[-1]-4, long(0))
        self.error = None
        self.registers = bytearray(0x200)
        self.blits = []
        self.read_ranges = {}
        self.write_ranges = {}
        self.phase = ''
        self.dma_accesses = []
        self.events = []
        self.mmio_events = []
        self.callbacks = []
        self.hook_memory(CUSTOM, CUSTOM + 0x1ff, self.mmio)
        self.hook_memory(FLAG, FLAG, lambda a, n, v: self.events.append((self.phase, 'flag-clear' if v & 255 == 0 else 'flag-set')))

    def hook_memory(self, start, end, callback):
        def wrapped(handle, kind, address, size, value, data):
            try:
                callback(address, size, value)
            except Exception as error:
                self.error = error
                u.uc_emu_stop(self.h)
        cb = C.CFUNCTYPE(None, P, I, Q, I, C.c_int64, P)(wrapped)
        self.callbacks.append(cb)
        handle = Z()
        ck(u.uc_hook_add(self.h, C.byref(handle), 1 << 11, cb, None, start, end))

    def intercept(self, address, action):
        def wrapped(handle, pc, size, user):
            try:
                action()
            except Exception as error:
                self.error = error
                ck(u.uc_emu_stop(self.h))
        cb = C.CFUNCTYPE(None, P, Q, I, P)(wrapped)
        self.callbacks.append(cb)
        handle = Z()
        ck(u.uc_hook_add(self.h, C.byref(handle), 4, cb, None, address, address))

    def return_call(self, result=None):
        if result is not None:
            self.reg(9, result)
        sp = self.reg(8)
        self.reg(18, self.get(sp, 4))
        self.reg(8, sp + 4)

    def write(self, address, data):
        ck(u.uc_mem_write(self.h, address, data, len(data)))

    def read(self, address, size):
        data = C.create_string_buffer(size)
        ck(u.uc_mem_read(self.h, address, data, size))
        return data.raw

    def get(self, address, size=2):
        return int.from_bytes(self.read(address, size), 'big')

    def reg(self, register, value=None):
        data = C.c_uint32(value or 0)
        ck(u.uc_reg_read(self.h, register, C.byref(data)) if value is None else
           u.uc_reg_write(self.h, register, C.byref(data)))
        return data.value

    def run(self, entry, args=b'', registers=None):
        self.reg(17, 0x2700)
        self.reg(5, DATA + 0x7ffe)
        self.reg(8, STACK)
        self.write(STACK, long(STOP) + args)
        for register, value in (registers or {}).items():
            self.reg(register, value)
        ck(u.uc_ctl(self.h, 10 | (1 << 30)))
        result = u.uc_emu_start(self.h, CODE + entry, STOP, 10000000, 2000000)
        if self.error:
            raise self.error
        ck(result)
        require(self.reg(18) == STOP, f'execution budget at O:{self.reg(18)-CODE:x}')

    def mmio(self, address, size, value):
        self.mmio_events.append((address - CUSTOM, size, value))
        if address == CUSTOM + 0x84:
            self.events.append((self.phase, 'COP2LC'))
        offset = address - CUSTOM
        self.registers[offset:offset + size] = (value & ((1 << (size * 8)) - 1)).to_bytes(size, 'big')
        if offset <= 0x58 < offset + size:
            self.blit()

    def dma(self, address, write=False, value=0):
        require(address % 2 == 0, 'unaligned DMA')
        require(0 <= address < 0x80000, 'DMA source/destination outside model Chip RAM')
        self.dma_accesses.append((self.phase, address, write))
        ranges = self.write_ranges if write else self.read_ranges
        lo, hi = ranges.get(self.phase, (address, address + 2))
        ranges[self.phase] = (min(lo, address), max(hi, address + 2))
        if write:
            self.write(address, word(value))
        else:
            return self.get(address)

    def blit(self):
        r = self.registers
        w = lambda off: int.from_bytes(r[off:off + 2], 'big')
        p = lambda off: int.from_bytes(r[off:off + 4], 'big')
        con0, con1, size = w(0x40), w(0x42), w(0x58)
        require(con1 & 0x1f == 0, 'unsupported line/fill/descending mode')
        width, height = size & 63 or 64, size >> 6 or 1024
        enabled = [(con0 >> shift) & 1 for shift in (11, 10, 9, 8)]
        ptrs = [p(off) for off in (0x50, 0x4c, 0x48, 0x54)]
        mods = [struct.unpack('>h', r[off:off + 2])[0] for off in (0x64, 0x62, 0x60, 0x66)]
        self.blits.append({'phase': self.phase, 'con0': con0, 'con1': con1,
                           'width_words': width, 'height': height, 'pointers': ptrs[:], 'modulos': mods})
        previous_a = previous_b = 0
        pending = None
        for y in range(height):
            for x in range(width):
                a, b, c = [self.dma(ptrs[i]) if enabled[i] else w(off)
                           for i, off in enumerate((0x74, 0x72, 0x70))]
                a &= w(0x44) if x == 0 else 0xffff
                a &= w(0x46) if x == width - 1 else 0xffff
                shifted_a = ((previous_a << 16) | a) >> (con0 >> 12) & 65535
                shifted_b = ((previous_b << 16) | b) >> (con1 >> 12) & 65535
                previous_a, previous_b = a, b
                d = 0
                for term in range(8):
                    if con0 & (1 << term):
                        d |= (shifted_a if term & 4 else ~shifted_a) & (shifted_b if term & 2 else ~shifted_b) & (c if term & 1 else ~c)
                if pending is not None:
                    self.dma(pending[0], True, pending[1])
                pending = (ptrs[3], d & 65535) if enabled[3] else None
                for i in range(4):
                    if enabled[i]:
                        ptrs[i] += 2
            for i in range(4):
                if enabled[i]:
                    ptrs[i] += mods[i]
        if pending is not None:
            self.dma(pending[0], True, pending[1])
        self.events.append((self.phase, 'blit-complete'))
        r[0x74:0x76], r[0x72:0x74] = word(previous_a), word(previous_b)
        for off, value in zip((0x50, 0x4c, 0x48, 0x54), ptrs):
            r[off:off + 4] = long(value)

    def setup(self, width, height, pixels, poison=0xa5):
        self.width, self.height = width, height
        self.row = (width + 15) // 16 * 2
        self.plane = self.row * (height + 2)
        self.size = self.plane * 4
        self.write(SOURCE - width * 2, bytes([poison]) * (width * (height + 4)))
        self.write(SOURCE, pixels)
        for base in (PLANES, WORK, OTHER):
            self.write(base - 64, bytes([0x5a]) * (self.size + 128))
            self.write(base, bytes(self.size))
        state = CODE + 0x331b8
        self.run(0x334e4, registers={1: state, 9: width, 10: height})
        require(self.get(state, 4) == self.size, 'native plane allocation differs')
        self.write(state + 4, long(WORK) + long(PLANES) + long(OTHER))
        self.write(SURFACE, bytes(32))
        self.write(SURFACE + 4, long(SOURCE))
        self.write(SURFACE + 20, word(width) + word(height))
        self.write(CODE + 0x324a8, long(SURFACE) + word(width) + word(height))
        self.write(CODE + 0x324b8, long(DESC) + long(DESC2))
        self.run(0x3257c)
        self.blits.clear()
        self.dma_accesses.clear()
        self.events.clear()
        self.mmio_events.clear()
        self.read_ranges.clear()
        self.write_ranges.clear()

    def convert(self, descriptor=DESC):
        for name, callback in (('first', 0x329e4), ('second', 0x32a26), ('final', 0x32dba)):
            self.phase = name
            self.events.append((name, 'start'))
            self.write(NODE + 18, long(descriptor + (50 if name == 'final' else 0)) + long(FLAG))
            self.write(FLAG, b'\xff')
            entry = callback
            for iteration in range(32):
                self.run(entry, registers={1: CUSTOM, 2: NODE})
                if self.reg(9) == 0:
                    break
                entry = self.get(NODE + 4, 4) - CODE
            else:
                raise ValueError('callback never completes')
            require(self.get(FLAG, 1) == 0, 'completion flag not cleared')
            self.events.append((name, 'complete'))

    def close(self):
        ck(u.uc_close(self.h))


def reference(pixels, width, height, native_edge=True):
    """Independent per-pixel dither selection and screen-bit packing.

    Native visible ViewPort is H-1 rows. The first odd row's four missing
    high-nibble pixels are a measured *functional-model* native edge quirk;
    retain and report it explicitly, never silently crop it out of the gate.
    """
    row = (width + 15) // 16 * 2
    out = bytearray(row * (height - 1) * 4)
    for y in range(height - 1):
        for x in range(width):
            colour = pixels[y * width + x] >> (4 if (x + y) % 2 == 0 else 0) & 15
            if native_edge and y == 1 and x in (1, 3, 9, 11):
                colour = 0
            for bit in range(4):
                if colour & (1 << bit):
                    out[bit * row * (height - 1) + y * row + x // 8] |= 0x80 >> (x % 8)
    return bytes(out)


def visible(cpu, base):
    return b''.join(cpu.read(base + bit * cpu.plane + 2 * cpu.row,
                             cpu.row * (cpu.height - 1)) for bit in range(4))


def pixel_cases(cpu):
    results = []
    representative = None
    rng = random.Random(0x13a2)
    for width, height in ((320, 200), (320, 166), (320, 128), (320, 16), (32, 16)):
        fixtures = {
            'all-colour-pairs': bytes(((i & 15) << 4) | ((i // 16 + 3) & 15)
                                     for i in range(width * height)),
            'random-independent-nibbles': bytes(rng.randrange(256) for _ in range(width * height)),
            'solid-white': bytes([255]) * (width * height),
        }
        for name, pixels in fixtures.items():
            cpu.setup(width, height, pixels)
            source_before = cpu.read(SOURCE - 2 * width, width * (height + 4))
            expected = reference(pixels, width, height)
            for descriptor, base, untouched in ((DESC, PLANES, OTHER), (DESC2, OTHER, PLANES)):
                other_before = cpu.read(untouched, cpu.size)
                cpu.convert(descriptor)
                require(visible(cpu, base) == expected, f'pixel mismatch: {width}x{height}/{name}')
                require(cpu.read(untouched, cpu.size) == other_before, 'other display buffer modified')
                require(cpu.read(SOURCE - 2 * width, width * (height + 4)) == source_before, 'source changed')
                for region in (PLANES, WORK, OTHER):
                    require(cpu.read(region - 64, 64) == bytes([0x5a])*64 and
                            cpu.read(region + cpu.size, 64) == bytes([0x5a])*64, f'planar allocation guard changed {width}x{height} {name} {region:x}')
                for phase, address, writing in cpu.dma_accesses:
                    if phase != 'final':
                        require(not writing or (base <= address < base + cpu.size or
                                WORK <= address < WORK + cpu.size or
                                untouched <= address < untouched + cpu.size), 'first-stage destination')
                    else:
                        require(not SOURCE - 2*width <= address < SOURCE + width*(height+2),
                                'final stage still consumes chunky source')
                require(len(cpu.blits) % (12 * (width // 16) + 18) == 0, 'wrong blit count')
            # Refill out-of-image reads with different poison: visible pixels
            # must not depend on adjacent allocations.
            cpu.write(SOURCE - 2*width, bytes([0x3c]) * (2*width))
            cpu.write(SOURCE + width*height, bytes([0xc3]) * (2*width))
            cpu.convert(DESC)
            require(visible(cpu, PLANES) == expected, 'visible pixels depend on overread padding')
            if representative is None:
                representative = {
                    'geometry': [width, height],
                    'blits': cpu.blits[:12*(width//16)+18],
                    'source_read_ranges_relative': {
                        phase: [min(address for ph, address, writing in cpu.dma_accesses
                                    if ph == phase and not writing and SOURCE-2*width <= address < SOURCE+width*(height+2))-SOURCE,
                                max(address+2 for ph, address, writing in cpu.dma_accesses
                                    if ph == phase and not writing and SOURCE-2*width <= address < SOURCE+width*(height+2))-SOURCE]
                        for phase in ('first', 'second')},
                    'range_end_exclusive': True}
            results.append({'width': width, 'height': height, 'visible_height': height-1,
                            'fixture': name, 'conversions': 3,
                            'blits_per_conversion': 12*(width//16)+18,
                            'visible_sha256': sha(expected)})
    # A naïve low-nibble CPU converter must fail the exact native contract.
    pixels = bytes([0xf0]) * (320 * 16)
    cpu.setup(320, 16, pixels)
    cpu.convert()
    require(visible(cpu, PLANES) != reference(bytes(320*16), 320, 16), 'wrong-nibble sabotage escaped')
    require(visible(cpu, PLANES) != reference(pixels, 320, 16, native_edge=False), 'native edge quirk missing')
    # Mutate the actual first callback's C mask, not the expected result.
    original = cpu.read(CODE + 0x32cba, 2)
    cpu.write(CODE + 0x32cba, word(0))
    cpu.setup(320, 16, pixels)
    cpu.convert()
    require(visible(cpu, PLANES) != reference(pixels, 320, 16), 'mask sabotage escaped')
    cpu.write(CODE + 0x32cba, original)
    # Native odd heights are outside the safe contract: keep this as a rejecting
    # control, not a silently removed failing positive fixture.
    cpu.setup(32, 17, bytes([255])*(32*17))
    cpu.convert()
    require(cpu.read(PLANES + cpu.size, 64) != bytes([0x5a])*64,
            'odd-height overrun control not reached')
    return {'fixtures': results, 'positive_conversions': len(results)*3,
            'negative_controls': ['low-nibble-only packing', 'omitted native model edge quirk',
                                  'native first callback C-mask mutation', 'odd-height allocation overrun'],
            'representative': representative}


def allocation_cases(game):
    cpu = Native(game)
    allocations, frees, active = [], [], {}
    fail_countdown = [0]
    cursor = {True: 0x20000, False: 0x190000}
    execbase = 0x8000
    cpu.write(4, long(execbase))
    # Only OS initialization/teardown is stubbed, not the native allocators,
    # allocation registry, descriptor construction or free paths under test.
    for offset in (0x33614, 0x33674):
        cpu.intercept(CODE + offset, lambda: cpu.return_call(1))
    def allocate():
        size, flags = cpu.reg(9), cpu.reg(10)
        if fail_countdown[0]:
            fail_countdown[0] -= 1
            if not fail_countdown[0]:
                cpu.return_call(0)
                return
        chip = bool(flags & 2)
        address = cursor[chip]
        cursor[chip] += (size + 7) & ~7
        active[address] = size
        allocations.append({'bytes': size, 'flags': flags, 'chip_requested': chip})
        cpu.write(address, bytes(size))
        cpu.return_call(address)
    def free():
        address, size = cpu.reg(2), cpu.reg(9)
        require(active.pop(address, None) == size, 'free pointer/size differs')
        frees.append(size)
        cpu.return_call()
    cpu.intercept(execbase - 198, allocate)
    cpu.intercept(execbase - 210, free)
    try:
        cpu.run(0x324c0, word(320) + word(200))
        require(cpu.reg(9) == 1, 'native display allocation failed')
        require([(a['bytes'], a['flags']) for a in allocations] ==
                [(96960, 0x10003), (668, 0x10001), (668, 0x10001)], 'display allocation contract')
        state = CODE + 0x331b8
        base = cpu.get(state + 8, 4)
        require(cpu.get(state + 4, 4) == base + 32320 and
                cpu.get(state + 12, 4) == base + 64640, 'workspace/display layout')
        # Native chunky wrapper, arbitrary rectangle origin and even row rounding.
        rectangle = 0x184000
        cpu.write(rectangle, struct.pack('>4h', 5, 7, 324, 206))
        cpu.run(0x31dc4, long(SURFACE) + long(rectangle))
        require([(a['bytes'], a['flags']) for a in allocations[-2:]] ==
                [(64000, 0x10003), (800, 0x10001)], 'chunky allocation contract')
        source, rows = cpu.get(SURFACE + 4, 4), cpu.get(SURFACE + 8, 4)
        require(cpu.get(SURFACE, 4) == rows - 28, 'row table origin bias')
        for y in range(200):
            require(cpu.get(rows + y*4, 4) == source - 5 + 320*y, 'row table stride')
        cpu.run(0x32476, long(SURFACE))
        require(cpu.get(SURFACE, 4) == 0 and cpu.get(SURFACE+4, 4) == 0 and
                cpu.get(SURFACE+8, 4) == 0, 'surface free did not clear pointers')
        # Public offscreen counterpart: no Chip or Fast guarantee.
        cpu.write(rectangle, struct.pack('>4h', 0, 0, 318, 15))
        cpu.run(0x31da8, long(SURFACE) + long(rectangle))
        require([(a['bytes'], a['flags']) for a in allocations[-2:]] ==
                [(5120, 0x10001), (64, 0x10001)], 'public surface allocation contract')
        cpu.run(0x32476, long(SURFACE))
        # Failure of the row table leaves the source in the native registry.
        fail_countdown[0] = 2
        cpu.run(0x31dc4, long(SURFACE) + long(rectangle))
        require(cpu.reg(9) == 0 and cpu.get(SURFACE+4,4) != 0 and
                cpu.get(SURFACE+8,4) == 0, 'native partial-allocation failure contract')
        cpu.run(0x32476, long(SURFACE))
        # Conversion idle + no active View: teardown can safely free descriptors
        # then the one combined allocation, never three separate region frees.
        cpu.intercept(CODE + 0x34076, lambda: cpu.return_call())
        cpu.run(0x32526)
        require(not active, 'native display teardown leaked a model allocation')
        require(frees[-3:] == [668, 668, 96960], 'display teardown order')
        return {'allocations': allocations, 'frees': frees,
                'partial_failure': 'row-table failure retains source until explicit surface cleanup',
                'os_stubbed': ['graphics initialization/restore', 'AllocMem', 'FreeMem', 'field wait']}
    finally:
        cpu.close()


def publication_cases(game):
    cpu = Native(game)
    try:
        cpu.setup(320, 16, bytes([0x12])*5120)
        state = CODE + 0x331b8
        cpu.write(CODE + 0x3352c, long(state))
        cpu.run(0x33aea)
        for index, base in enumerate((PLANES, OTHER)):
            bitmap = CODE + 0x335b4 + index*40
            require(cpu.get(bitmap) == 40 and cpu.get(bitmap+2) == 16 and
                    cpu.get(bitmap+5, 1) == 4, 'bitmap geometry/depth')
            require([cpu.get(bitmap+8+i*4,4) for i in range(8)] ==
                    [base+80+i*cpu.plane for i in range(4)]+[0]*4, 'bitmap plane pointers')
        cpu.write(state+30, word(1)+word(0))
        cpu.run(0x33426)
        require(cpu.get(state+30) == 0 and cpu.get(state+32) == 1, 'buffer rotation')
        gfx = 0x9000
        cpu.write(CODE+0x33518, long(gfx))
        lists = (0x1a000, 0x1b000)
        for index, pointer in enumerate(lists):
            structure = 0x184000 + index*32
            cpu.write(structure+4, long(pointer))
            cpu.write(CODE+0x3360c+index*4, long(structure))
        cpu.write(CODE+0x33a6c, word(-1))
        cpu.write(DATA+0x77ae, word(-1))
        cpu.convert(DESC2)
        require(cpu.get(CODE+0x33530) == 1, 'completion did not select pending buffer')
        require(cpu.get(gfx+50,4) == lists[1] and cpu.get(gfx+54,4) == lists[1], 'graphics Copper pointer')
        require(cpu.get(CUSTOM+0x84,4) == lists[1], 'COP2LC publication')
        final = [kind for phase,kind in cpu.events if phase == 'final']
        require(final.count('blit-complete') == 18 and
                max(i for i,x in enumerate(final) if x == 'blit-complete') < final.index('flag-clear') < final.index('COP2LC'),
                'publication before completion')
        require(cpu.get(CODE+0x32916,4) == cpu.get(DATA+0x77fe,4), 'completion clock snapshot')
        # Direct planar writer is a second independent check of nibble/bit order.
        cpu.write(state+30, word(0))
        for colour in range(16):
            cpu.run(0x333b4, word(colour) + word(4) + word(colour))
        row = cpu.read(PLANES+80+4*40, 2)
        require(row == bytes([0x55, 0x55]), 'direct pixel bit zero order')
        for bit in range(4):
            expected = sum(((x>>bit)&1) << (15-x) for x in range(16))
            require(cpu.get(PLANES+80+bit*cpu.plane+4*40) == expected, 'direct plane order')
        # Offscreen coordinates must be rejected without touching display memory.
        after = cpu.read(PLANES, cpu.size)
        for x,y in ((320,0),(0,16),(65535,0)):
            cpu.run(0x333b4, word(x)+word(y)+word(15))
        require(cpu.read(PLANES,cpu.size) == after, 'direct writer clipping failed')
        # Whole-plane clear includes both leading pad rows and bypasses chunky.
        cpu.write(state+34, b'\xff')
        cpu.run(0x33348, word(5))
        require(cpu.read(PLANES,cpu.size) == b''.join(bytes([255 if 5&(1<<b) else 0])*cpu.plane
                                                   for b in range(4)), 'direct planar clear')
        return {'bitmap_cases': 2, 'direct_colours': 16, 'clipping_cases': 3,
                'publication': 'final callback selects rotated buffer and writes COP2LC',
                'beam_timing_validated': False}
    finally:
        cpu.close()


def queue_cases(game):
    """Execute native submission/waits with explicit abstract QBlit scheduling.
    Callback pixels are tested separately. No nested emulation or pretend VBL.
    """
    cpu = Native(game)
    queue, waits = [], []
    complete_final = [False]
    flags = [CODE + offset for offset in (0x3291a, 0x3291b, 0x3291c)]
    gfx = 0x9000
    cpu.write(CODE+0x33518, long(gfx))
    cpu.write(CODE+0x32916, long(0))
    cpu.write(DATA+0x77fe, long(1))  # satisfy the explicit between-stage field wait
    def enqueue():
        node = cpu.reg(2)
        flag = cpu.get(node+22,4)
        require(cpu.get(flag,1) == 255, 'queue node was not marked busy')
        queue.append({'node_hunk_offset': f'{node-CODE:x}',
                      'callback_hunk_offset': f'{cpu.get(node+4,4)-CODE:x}',
                      'flag_hunk_offset': f'{flag-CODE:x}',
                      'payload': cpu.get(node+18,4)})
        cpu.return_call()
    def wait():
        flag = cpu.get(cpu.reg(8)+4,4)
        require(flag in flags, 'unknown completion owner')
        if cpu.get(flag,1):
            waits.append(f'{flag-CODE:x}')
            require(flag != flags[2] or complete_final[0], 'final conversion still owns destination')
            cpu.write(flag,b'\x00')
        cpu.return_call()
    cpu.intercept(gfx-276, enqueue)
    cpu.intercept(CODE+0x3407e, wait)
    try:
        cpu.run(0x3291e, long(DESC))
        require([q['callback_hunk_offset'] for q in queue] == ['329e4','32a26','32dba'], 'queue callback order')
        require([q['payload'] for q in queue] == [DESC,DESC,DESC+50], 'queue payload owners')
        require(waits == ['3291a','3291b'], 'submission did not wait for both source readers')
        require([cpu.get(f,1) for f in flags] == [0,0,255], 'final should remain pending at return')
        # Do not let the next frame rotate while that destination remains owned.
        cpu.write(CODE+0x331d6, word(1)+word(0))
        try:
            cpu.run(0x3260a)
        except ValueError as error:
            require('still owns' in str(error), 'wrong ownership rejection')
            cpu.error = None
        else:
            raise ValueError('destination reused before final completion')
        require(cpu.get(CODE+0x331d6) == 1 and cpu.get(CODE+0x331d8) == 0, 'rotation preceded final wait')
        complete_final[0] = True
        cpu.run(0x32990)
        require(cpu.get(flags[2],1) == 0, 'final wait did not retire conversion')
        return {'queue': queue, 'waits': waits,
                'source_reusable_on_submit_return': True,
                'destination_reusable_only_after_final': True,
                'scheduling': 'abstract host services; no OS queue or beam timing claim'}
    finally:
        cpu.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = new_output(args.output)
    out.mkdir(parents=True)
    cpu = Native(ROOT / 'tmp/originals/ocs/WingCommander/data/Wing.english')
    try:
        results = pixel_cases(cpu)
        allocations = allocation_cases(ROOT / 'tmp/originals/ocs/WingCommander/data/Wing.english')
        publication = publication_cases(ROOT / 'tmp/originals/ocs/WingCommander/data/Wing.english')
        queue = queue_cases(ROOT / 'tmp/originals/ocs/WingCommander/data/Wing.english')
        (out / 'queue.json').write_text(json.dumps(queue, indent=2) + '\n')
        (out / 'allocation.json').write_text(json.dumps(allocations, indent=2) + '\n')
        (out / 'publication.json').write_text(json.dumps(publication, indent=2) + '\n')
        (out / 'blits.json').write_text(json.dumps(results.pop('representative'), indent=2) + '\n')
        (out / 'report.json').write_text(json.dumps({
            'game_sha256': GAME_SHA, 'status': 'pass',
            'scope': 'isolated M68000 instructions and functional ascending area blitter',
            'not_validated': ['OS queue scheduling', 'beam deadlines', 'bus contention',
                              'full boots', 'hardware compatibility', 'performance'],
            'positive_conversions': results['positive_conversions'],
            'model_edge_quirk_requires_live_confirmation': True}, indent=2) + '\n')
        (out / 'pixels.json').write_text(json.dumps(results, indent=2) + '\n')
        print('passed pixel fixtures:', len(results['fixtures']))
    finally:
        cpu.close()


if __name__ == '__main__':
    main()
