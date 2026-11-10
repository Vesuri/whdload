#!/usr/bin/env python3
"""Execute the 20-ms opponent movement (timing_opponent_motion.s) against native code with Unicorn.

Source ../../common/env.sh first. Requires vasm, AMIGA_UNICORN and the extracted game
(tmp/extracted/pd, `make unpack`); its code hunk runs from memory only.

1. timing_opponent_motion_place must rebuild exactly what the native update computes from
   the same progress: position, heading and segment ($d5d2..$d69e) and the player distance
   ($d724..$d75a), on random path nodes and progress values within the lap.
2. timing_opponent_motion_predict must give the native advance of the next update
   ($d558..$d5d2 after the $64 decrement), for random speed, fuel, mode and damage
   countdown, with the native random draw at $53f6 returning 0 (no +-40).
3. Across random sequences of native-style updates (the authoritative progress gains the
   predicted advance plus a random +-40, sometimes with a lap wrap or a reposition) and
   4-5 world steps after each: restore hands every update its authoritative progress, the
   shown progress never decreases within a lap, never reaches the lap line before the
   update that counts the lap, and is never more than one update plus the snap limit away
   from the authoritative progress.
4. With the gate closed (grid before the start, pause, menus) the step and the bounce leave
   the tracked records unchanged whatever D0 holds, since the gate's result is in the flags.
"""
import ctypes as C
import os
from pathlib import Path
import random
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
out = root / 'tmp/opponent-motion'
out.mkdir(parents=True, exist_ok=True)
GAME, HARNESS, ARENA, RECORDS, PATH = 0x10000, 0x200000, 0x300000, 0x340000, 0x360000
STATE = GAME + 0xa6e
SLOT = ARENA + 0x9600
(out/'harness.s').write_text(f''' org ${HARNESS:x}
 dc.l place,predict,restore,capture,step,bounce,gate
place
 bsr timing_opponent_motion_place
 rts
predict
 bsr timing_opponent_motion_predict
 rts
restore
 bsr timing_opponent_motion_restore
 rts
capture
 bsr timing_opponent_motion_capture
 rts
step
 bsr timing_opponent_motion_step
 rts
bounce
 bsr timing_opponent_motion_bounce
 rts
TIMING_PERIOD = 18
; Like the real gate: the result is in Z, D0 comes back unchanged.
timing_opponent_effects_enabled
 tst.w gate
 rts
gate dc.w 1
perf_arena dc.l ${ARENA:x}
perf_game dc.l ${GAME:x}
timing_world_state dc.l 0,0
 dc.w 1
timing_pit_state dc.l 0,0
 dc.w 0
timing_opponent_effects_state dc.l 0,0,0,0
 INCLUDE timing_opponent_motion.s
''')
subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin', '-I'+str(root/'src'),
                '-o', str(out/'harness.bin'), str(out/'harness.s')], check=True, stdout=subprocess.DEVNULL)

game = (root/'tmp/extracted/pd').read_bytes()
assert struct.unpack_from('>I', game, 24)[0] == 0x3e9
size = struct.unpack_from('>I', game, 28)[0]*4
code = bytearray(game[32:32+size])
pos = 32+size
assert struct.unpack_from('>I', game, pos)[0] == 0x3ec
pos += 4
while (count := struct.unpack_from('>I', game, pos)[0]):
    pos += 8
    for off in struct.unpack_from(f'>{count}I', game, pos):
        struct.pack_into('>I', code, off, struct.unpack_from('>I', code, off)[0]+GAME)
    pos += count*4

lib = C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
ptr, u64, sz = C.c_void_p, C.c_uint64, C.c_size_t
for n, signature in {'uc_open': [C.c_int, C.c_int, C.POINTER(ptr)], 'uc_mem_map': [ptr, u64, sz, C.c_uint],
                     'uc_mem_write': [ptr, u64, ptr, sz], 'uc_mem_read': [ptr, u64, ptr, sz], 'uc_reg_write': [ptr, C.c_int, ptr],
                     'uc_reg_read': [ptr, C.c_int, ptr], 'uc_emu_start': [ptr, u64, u64, u64, sz]}.items():
    getattr(lib, n).argtypes = signature
lib.uc_ctl.argtypes = [ptr, C.c_uint]


def ok(err):
    assert err == 0, f'Unicorn error {err}'


uc = ptr()
ok(lib.uc_open(7, 1 << 30, C.byref(uc)))
ok(lib.uc_ctl(uc, C.c_uint(7 | 1 << 26 | 1 << 30), C.c_int(2)))  # 68020
ok(lib.uc_mem_map(uc, 0, 0x400000, 7))


def write(addr, data): ok(lib.uc_mem_write(uc, addr, bytes(data), len(data)))


def read(addr, n):
    b = C.create_string_buffer(n)
    ok(lib.uc_mem_read(uc, addr, b, n))
    return b.raw


def reg(n, value=None):
    v = C.c_uint32(0 if value is None else value & 0xffffffff)
    if value is None:
        ok(lib.uc_reg_read(uc, n, C.byref(v)))
        return v.value
    ok(lib.uc_reg_write(uc, n, C.byref(v)))


D = [9 + i for i in range(8)]
A = [1 + i for i in range(8)]
PC, END = 18, 0x3f0000
write(GAME, code)
write(GAME+0x53f6, bytes.fromhex('70004e75'))            # random: moveq #0,d0 / rts
blob = (out/'harness.bin').read_bytes()
write(HARNESS, blob)
entries = dict(zip(('place', 'predict', 'restore', 'capture', 'step', 'bounce', 'gate'), struct.unpack_from('>7I', blob)))
write(GAME+0x682, struct.pack('>I', PATH))


def run(start, stop=END, **regs):
    for name, value in regs.items():
        reg((D if name[0] == 'd' else A)[int(name[1])], value)
    reg(A[6], STATE)
    reg(A[7], 0x3e0000)
    write(0x3e0000, struct.pack('>I', END))
    ok(lib.uc_emu_start(uc, start, stop, 0, 200000))
    assert reg(PC) == stop, hex(reg(PC))


s16 = lambda b, o: struct.unpack_from('>h', b, o)[0]
rng = random.Random(4321)


def new_path(nodes):
    data = bytearray()
    for _ in range(nodes):
        data += struct.pack('>hhhbB', *(rng.randrange(-20000, 20000) for _ in range(3)),
                            rng.randrange(-128, 128), rng.randrange(256))
    write(PATH, data)
    write(STATE+0x368, struct.pack('>h', nodes*8))
    return nodes*8*16


def record_fields(addr):
    b = read(addr, 0xbe)
    return [s16(b, 0x10), s16(b, 0x12), s16(b, 0x14), s16(b, 0x20), s16(b, 2), struct.unpack_from('>i', b, 0x4c)[0]]


# 1. Placement against native.
places = 0
for path in range(40):
    lap = new_path(rng.randrange(3, 400))
    for case in range(250):
        p = rng.choice([rng.randrange(lap), lap-1, rng.randrange(min(lap, 256))])
        player = [rng.randrange(-32768, 32768) for _ in range(3)]
        write(STATE+0x12c, struct.pack('>hhh', *player))
        record = bytearray(rng.randbytes(0xbe))
        struct.pack_into('>i', record, 0x66, p)
        write(RECORDS, record)
        run(GAME+0xd5d2, GAME+0xd69e, a4=PATH, a5=RECORDS)
        run(GAME+0xd724, GAME+0xd75a, a5=RECORDS)
        native = record_fields(RECORDS)
        write(RECORDS, record)
        run(entries['place'], d0=p, a4=PATH, a5=RECORDS)
        assert record_fields(RECORDS) == native, (path, case, p, native, record_fields(RECORDS))
        places += 1

# 2. Prediction against native.
predictions = 0
for case in range(20000):
    record = bytearray(0xbe)
    speed = rng.randrange(0, 1400)
    fuel = rng.choice([-1, 0, 1, 30000])
    countdown = rng.choice([0, -1, 1, 2, 5, 8, 9, 10, 20])
    mode = rng.choice([-1, 0, 5])
    struct.pack_into('>hhh', record, 0x16, speed, 0, 0)
    struct.pack_into('>h', record, 0x48, fuel)
    struct.pack_into('>h', record, 0x64, countdown)
    write(STATE+0x4b8, struct.pack('>i', mode))
    write(STATE+0x21c, struct.pack('>h', 18))
    write(RECORDS, record)
    run(entries['predict'], a1=SLOT, a5=RECORDS)
    predicted = s16(read(SLOT, 16), 12)
    after = countdown - 1 if countdown > 0 else countdown
    if after > 8:
        expected = 0
    else:
        struct.pack_into('>h', record, 0x64, after)
        struct.pack_into('>i', record, 0x66, 0)
        write(RECORDS, record)
        run(GAME+0xd558, GAME+0xd5d2, a5=RECORDS)
        expected = max(struct.unpack_from('>i', read(RECORDS+0x66, 4))[0], 0)
    assert predicted == expected, (case, speed, fuel, countdown, mode, predicted, expected)
    predictions += 1

# 3. Update/step sequences.
OPPONENTS = 4
sequences = wraps = snaps = 0
for sequence in range(300):
    lap = new_path(rng.randrange(40, 400))
    write(STATE+0x340, struct.pack('>hI', OPPONENTS-1, RECORDS))
    write(STATE+0x4b8, struct.pack('>i', -1))
    write(STATE+0x2e8, struct.pack('>h', 0))
    write(SLOT, bytes(16*32))
    authority = [rng.randrange(lap) for _ in range(OPPONENTS)]
    speed = [rng.randrange(100, 1400) for _ in range(OPPONENTS)]
    for i in range(OPPONENTS):
        record = bytearray(0xbe)
        struct.pack_into('>h', record, 0x16, speed[i])
        struct.pack_into('>h', record, 0x48, 30000)
        struct.pack_into('>i', record, 0x66, authority[i])
        write(RECORDS+i*0xbe, record)
    shown = [None]*OPPONENTS
    for update in range(60):
        if update:
            run(entries['restore'])
        current = [struct.unpack_from('>i', read(RECORDS+i*0xbe+0x66, 4))[0] for i in range(OPPONENTS)]
        assert current == authority, (sequence, update, current, authority)
        moved = [False]*OPPONENTS
        for i in range(OPPONENTS):
            v = speed[i]*18//26
            gain = max(v, 40) + rng.choice([0, 0, 0, 40, -40])
            value = authority[i] + gain
            if rng.random() < 0.01:
                value = rng.randrange(lap)         # reposition
                moved[i] = True
                snaps += 1
            elif value >= lap:
                value = 0                          # the native lap reset at $d84a
                wraps += 1
            authority[i] = value
            write(RECORDS+i*0xbe+0x66, struct.pack('>i', value))
        run(entries['capture'])
        for world in range(rng.choice([4, 5])):
            run(entries['step'])
            for i in range(OPPONENTS):
                slot = read(SLOT+i*32, 32)
                a, p, written = struct.unpack_from('>iii', slot, 0)
                flags = slot[25]
                value = struct.unpack_from('>i', read(RECORDS+i*0xbe+0x66, 4))[0]
                assert value == written == p and 0 <= p < lap, (sequence, update, i, value, written, p, lap)
                if shown[i] is not None and p < shown[i] and not moved[i]:
                    # Only a lap carried across the line, from the second half to the first.
                    assert shown[i] >= lap//2 and p < lap//2 and not flags & 2, (sequence, update, i, shown[i], p)
                gap = (a + (lap if flags & 2 else 0)) - p
                assert abs(gap) <= 2*(1400*18//26 + 40) + 1024, (sequence, update, i, a, p, flags)
                shown[i] = p
    sequences += 1

# 4. A closed gate (grid, pause, menus) leaves every record alone, whatever D0 holds.
write(entries['gate'], struct.pack('>h', 0))
closed = 0
for case in range(200):
    for i in range(OPPONENTS):
        record = bytearray(rng.randbytes(0xbe))
        struct.pack_into('>h', record, 0x56, 0)
        struct.pack_into('>h', record, 0x8, 0)
        struct.pack_into('>h', record, 0x3c, 1)
        struct.pack_into('>h', record, 0x16, rng.randrange(100, 1400))
        struct.pack_into('>i', record, 0x66, rng.randrange(lap))
        write(RECORDS+i*0xbe, record)
    write(STATE+0x2f0, struct.pack('>h', 0))
    write(STATE+0xb6, struct.pack('>h', 0))
    run(entries['capture'])                    # the slots track these records
    before = read(RECORDS, OPPONENTS*0xbe)
    run(entries['step'], d0=rng.randrange(1, 1 << 32))
    run(entries['bounce'], d0=rng.randrange(1, 1 << 32))
    assert read(RECORDS, OPPONENTS*0xbe) == before, case
    closed += 1
print(f'{closed} closed-gate steps leave the records unchanged')
print(f'{places} placements and {predictions} predictions match native code; '
      f'{sequences} update/step sequences ({wraps} lap wraps, {snaps} repositions) keep their bounds')
