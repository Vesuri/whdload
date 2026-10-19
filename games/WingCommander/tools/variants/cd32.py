# Verified English definitions. Addresses are hunk offsets, never live addresses.
# See docs/internals.md; missing entries are deliberately unavailable.
NAME = 'cd32'
CPU = '68020'
GAME = 'tmp/originals/cd32/WingCommanderCD32/data/wing.english'
GAME_SHA = '093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657'
SLAVE = 'tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave'
SLAVE_SHA = '5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986'
SLAVE_SIZE = 0x1e0c
# file payload base, stored bytes, allocated bytes; None denotes BSS.
HUNKS = ((0x2c,0x35ea4,0x35ea4),(0x3a048,0x8464,0xfda0),
         (None,0,4),(0x42dec,0x1590,0x1590))
A4_BASE = 0x7ffe
SIGNATURE = (0x34002, 0x3402e)
NATIVE = dict(world=0x2a8, draw=0x2e4, finish=0xc40, asteroids=0x98a2,
              object_dispatch=0x7b4e, position=0x80b6, publish=0x3378e)
A4 = dict(field_clock=-252, world_count=4430, draw_count=4434,
          position=0x119c, velocity=0x1d6e, object_class=0x1700)
OBJECTS = dict(world_slots=61, pose_storage_slots=64)
BITMAP = dict(width=320, depth=8, leading_rows=0,
              converter_heights=(128,166,200), colour='byte')
SCENE = dict(title_updates=296, approach=135, departure=235,
             credit_pages=18, text_fields=220, page_fields=320)
# Guard width applies only to non-absolute-JSR sites; JSRs guard relocated targets.
WIDE_GUARDS = (0x28c86,0x7bc2,0x878,0x65f4,0x4b16,0x101c,0x438,0x3b8e,0x3378e,0x1fe44)
TIMING_HOOKS = (
    (0x28c86, 'timing_debris_draw', 0x4ef9),
    (0x698, 'timing_loop', 0x4ef9),
    (0x878, 'timing_pause', 0x4ef9),
    (0x101c, 'timing_autopilot', 0x4ef9),
    (0x18eee, 'timing_throttle_gate', 0x4eb9),
    (0x18f00, 'timing_throttle_gate', 0x4eb9),
    (0x18f3a, 'timing_fire_gate', 0x4eb9),
    (0x7bc2, 'timing_world_rotation', 0x4eb9),
    (0x34188, 'timing_record_input', 0x4eb9),
    (0x1934c, 'timing_pad_read', 0x4eb9),
    (0x18c6a, 'timing_keys_read', 0x4eb9),
    (0x19380, 'timing_key_command', 0x4eb9),
    (0x65f4, 'timing_emission_clock', 0x4eb9),
    (0x51a, 'timing_message_draw', 0x4eb9),
    (0x46ea, 'timing_systems_draw', 0x4eb9),
    (0x530, 'timing_sim_draw', 0x4ef9),
    (0x438, 'timing_sim_score_draw', 0x4eb9),
    (0x3b8e, 'timing_target_draw', 0x4ef9),
    (0x4b16, 'timing_selection', 0x4ef9),
    (0x435c, 'timing_portrait_clock', 0x4eb9),
    (0x43ee, 'timing_portrait_random', 0x4eb9),
)
BUFFERED_HOOKS = (
    (0x81a4, 'field_shot_query', 0x4eb9),
    (0x30c, 'waypoint_early', 0x4eb9),
    (0x320, 'waypoint_scene', 0x4eb9),
    (0x1de20, 'cinematic_background', 0x4eb9),
    (0x1de3c, 'cinematic_background', 0x4eb9),
    (0x1df50, 'cinematic_background', 0x4eb9),
    (0x1df6c, 'cinematic_background', 0x4eb9),
    (0x32e, 'intro_asteroids_draw', 0x4eb9),
    (0x2f8, 'intro_flash_draw', 0x4eb9),
    (0x1fd00, 'intro_title', 0x4ef9),
    (0x1fdda, 'intro_credits_update', 0x4eb9),
    (0x1fde0, 'intro_draw', 0x4eb9),
    (0x1fe14, 'intro_finish', 0x4eb9),
    (0x1fe44, 'intro_credits_end', 0x4ef9),
    (0xc912, 'projectile_gun_return', 0x4ef9),
    (0xca5e, 'projectile_missile_return', 0x4ef9),
    (0xc316, 'projectile_effect_return', 0x4ef9),
    (0x9a52, 'projectile_init_return', 0x4ef9),
    (0x306, 'view_clear', 0x4eb9),
    (0xc4c, 'view_compose', 0x4eb9),
    (0x2b648, 'timing_scene_allocate', 0x4ef9),
    (0x807a, 'translation_velocity', 0x4ef9),
    (0x80b6, 'translation_position', 0x4ef9),
    (0x3378e, 'release_publish', 0x4ef9),
    (0x337ea, 'release_teardown', 0x4ef9),
)
