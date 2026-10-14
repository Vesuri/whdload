# Verified English definitions. Addresses are hunk offsets, never live addresses.
# See docs/internals.md; missing entries are deliberately unavailable.
NAME = 'ocs'
CPU = '68000'
GAME = 'tmp/originals/ocs/WingCommander/data/Wing.english'
GAME_SHA = 'eff90d6cfbc80b008e5e508ff6488f221b6e7243958aaff6fdfd0b06e6724a30'
SLAVE = 'tmp/originals/ocs/WingCommander/WingCommander.Slave'
SLAVE_SHA = 'eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913'
SLAVE_SIZE = 0x14a8
HUNKS = ((0x2c,0x358c8,0x358c8),(0x39948,0x7bb8,0xf5b8),
         (None,0,4),(0x41e4c,0x1d94,0x1d94))
A4_BASE = 0x7ffe
SIGNATURE = (0x34082,0x340b0)
NATIVE = dict(world=0x2be, draw=0x2e6, finish=0xb80, asteroids=0x9618,
              object_dispatch=0x78c4, position=0x7e2c, publish=0x3385a)
A4 = dict(field_clock=-0x800, world_count=0x8dc, draw_count=0x8e0,
          position=0x92a, velocity=0x14fc, object_class=0xe8e)
# Only native dispatch bounds are established; do not borrow CD32 storage sizes.
OBJECTS = dict(world_slots=61)
BITMAP = dict(width=320, depth=4, row_alignment=16, leading_rows=2,
              colour='checkerboard-nibbles', viewport_height_adjust=-1)
SCENE = dict(title_updates=296, approach=135, departure=235,
             credit_pages=15, text_fields=220, page_fields=320)
# Selector instruction, CRC, original patch-list offset in the slave hunk.
SELECTORS = ((0x115c,0x116d,0x12bc),(0x1166,0x00e8,0x1302),(0x1170,0x262d,0x1348))
# Verified original English hook targets, not an enhanced timing patch list.
ORIGINAL_HOOKS = dict(audio=(0,0x26a3c,0x13a0), clear=(0,0x272b2,0x138e))
# No CD32 TIMING_HOOKS/BUFFERED_HOOKS. The separate OCS candidate links
# its D2 adapter through ocs_clock_source; responsive prediction remains D3.
