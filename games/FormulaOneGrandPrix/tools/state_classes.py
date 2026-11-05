"""Reviewed A3 ownership ranges for the pinned 582992-byte game.
Ranges are half-open. These classify observed NET deltas, not all possible stores.
The separate renderer audit covers transient and same-value stores statically.
"""
# Interrupt-owned values can change across any call, including drawing.
ASYNC = {
    0: [(0x125e,0x1260),(0x2578c,0x25791),(0x2cc06,0x2cc07),
        (0x3a704,0x3a706),(0x3a928,0x3a92c)],
    2: [(0,0x20),(0x28c,0x292),(0x93a,0x93c),(0x1dab0,0x1dab1),(0x1e2dc,0x1e2e2)],
}
TICK = {0: [(0x257c4,0x257c9),(0x3a746,0x3a74e),(0x3a770,0x3a774),(0x3a820,0x3a824)]}
WORK = {
    0: [(0x1348,0x1372),(0x147a,0x147c),(0x1e802,0x1e804),
        (0x1e968,0x1e96a),(0x1eb4e,0x1eb4f),(0x1f03a,0x1f040),
        (0x1f37e,0x1f388),(0x222dc,0x222f0),(0x25644,0x25648),
        (0x2e2ec,0x2e2f0),(0x2e3ea,0x2e3ec),(0x2e4d6,0x2e4d8),
        (0x31b96,0x31b98),(0x32448,0x32449),(0x32693,0x32694),
        (0x327f0,0x327f1),(0x3a828,0x3a82a)],
    1: [(0,0x220),(0x1ad6,0x1b3e),(0x16294,0x16c4a),
        (0x1c3fc,0x21d76),(0x21d7e,0x22b00)],
    2: [(0x1e13c,0x1e13d),(0x1e278,0x1e65c),(0x1e804,0x1e810),
        (0x1f4e6,0x1f562),(0x23126,0x231ea),(0x23220,0x23224),
        (0x2324a,0x2327e),(0x28168,0x281ac),(0x29e16,0x29e2c),
        (0x2a08e,0x2a090),(0x2c3bf,0x2c3c0)],
    3: [(0x112f8,0x14f84)],
}


def contains(table,h,off):
    return any(a<=off<b for a,b in table.get(h,()))


def draw_class(h,off):
    if contains(ASYNC,h,off): return 'asynchronous'
    if contains(TICK,h,off): return 'tick-side-effect'
    if contains(WORK,h,off): return 'presentation-workspace'
    # 46-byte track records: visibility/association flags and packed clipping cache.
    if h==1 and 0x2bfa<=off<0x16294 and (off-0x2bfa)%46 in (0xa,0x1e,0x25,0x26,0x2a,0x2b):
        return 'presentation-track-flags'
    return 'UNCLASSIFIED'


# Call TARGET, not call-site: live and replay share implementations.
CALLS = {
    (0,0x396ac): 'tick: replay state recording',
    (0,0x64): 'tick: keyboard mask consumption',
    (0,0x34d24): 'tick: controller consumption',
    (0,0x3bbf6): 'tick/modal: assistance and control edges',
    (0,0x39654): 'tick: replay input recording',
    (0,0x395f2): 'tick: replay input playback',
    (0,0x3b5de): 'tick/modal: pause and view keys',
    (0,0x3b80e): 'tick/modal: pause and resume',
    (0,0x3b346): 'tick: session, start lights and race events',
    (0,0x2ac14): 'mixed: cars, AI, physics, sound, track state and embedded HUD writes',
    (0,0x3bf96): 'tick: camera selection and edge latches',
    (0,0x3c55c): 'mixed: cockpit/background rebuild and refresh latch',
    (0,0x34028): 'mixed: camera evolution and projection inputs',
    (2,0x280f6): 'mixed: renderer; classify each changed byte',
    (0,0x258a2): 'tick: game clocks and session deadlines',
    (0,0x39542): 'mixed: cockpit instruments and pit/UI trigger latches',
    (2,0x1dfb4): 'presentation: replay R overlay',
    (0,0x2dd74): 'mixed: HUD drawing, dirty flags and blink phase',
    (0,0x1272): 'presentation/sound: pacing and display publication',
    (2,0x51c): 'input predicate: no game-state writes',
    (2,0x8e2): 'modal/hardware: interrupt and sound handoff',
    (0,0x29c1c): 'modal/tick: race classification',
    (0,0x3b1e0): 'modal/tick: finish-session state',
}
