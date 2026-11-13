"""D3 compile-time OCS adapters for owned CD32 prediction algorithms.

Maps name verified OCS operands, not a global relocation delta. Native bytes
remain generated under tmp; normal CD32 sources and builds are unchanged.
"""
import re
from shared_cpu import select
from german_map import english

# A4 offsets: pose, basis, control and projection fields, verified against the
# OCS native rotation/acceleration/geometry and constructor routines.
FIELDS={0x119c:0x92a,0x1d6e:0x14fc,0x1700:0xe8e,0x17f8:0xf86,
 0x14c8:0xc56,0x1566:0xcf4,0x157a:0xd08,0x15fa:0xd88,0x167a:0xe08,
 0x16fa:0xe88,0x16fc:0xe8a,0x16fe:0xe8c,0x214a:0x18d8,
 0x3452:0x2a40,0x3752:0x2d40,0x2e6e:0x23fc,0x1afc:0x128a,
 0x33cc:0x29ba,0x18c8:0x1056,0x2c6e:0x21fc,0x2d6e:0x22fc,
 0x3a6a:0x3058,0x4078:0x3666,0x40f8:0x36e6,0x2dee:0x237c,
 0x245e:0x20f8,0x24de:0x252e,0x255e:0x550c,0x2bea:0x2178,
 0x2cee:0x227c,0x3b86:0x3174,0x19c0:0x114e,0x3aea:0x30d8,
 0x3b2e:0x311c,0x3b16:0x3104,0x3a54:0x3042,
 0x3b3a:0x3128,0x155c:0xcea,-18296:-18334,-18278:-18316,
 -32109:-32085,-18280:-18318,-29978:-29954,-11354:-11224}
CALLS={0x2c8dc:0x2b950,0x1597e:0x156e6,0x18daa:0x183e4,0x742:0x73e,0x6fe:0x6fa,0xccda:0xca50,
 0x7c86:0x79fc,0x2acb2:0x29d26,0x2acf2:0x29d66,0x2ad32:0x29da6,
 0x2a820:0x29894,0x680e:0x6584,0x2a086:0x290fa,0x2b7f0:0x2a864,
 0x7f78:0x7cee,0x8080:0x7df6,0x80ea:0x7e60,0x80bc:0x7e32}
HOOKS=((0x7f1a,'field_shot_query',0x4eb9),(0x29114,'ocs_input_geometry_class',0x4eb9),(0x7938,'timing_world_rotation',0x4eb9),
 (0x7df0,'translation_velocity',0x4ef9),(0x7e2c,'translation_position',0x4ef9),
 (0x18574,'timing_fire_gate',0x4eb9),(0x18528,'timing_throttle_gate',0x4eb9),
 (0x1853a,'timing_throttle_gate',0x4eb9),
 (0xc688,'ocs_projectile_gun',0x4ef9),(0xc08c,'projectile_effect_return',0x4ef9),
 (0xc7d4,'projectile_missile_return',0x4ef9),(0x97c8,'projectile_init_return',0x4ef9),
 (0x182de,'ocs_input_pad',0x4eb9),(0x182e8,'ocs_input_keys',0x4eb9),
 (0x18d2e,'ocs_input_command',0x4eb9))
NOPS=(0x793e,)

def number(v):return int(v[1:],16) if v.startswith('$') else int(v)

def field(v):
    n=number(v)
    if n in FIELDS:return str(FIELDS[n])
    # Explicit three-long vectors; camera/scratch storage is the same 64 slots.
    for old in (0x119c,0x214a,0x3452,0x3752,0x1d6e,0x3b86):
        if n in (old+4,old+8,old+61*12):return str(FIELDS[old]+n-old)
    raise ValueError('unmapped OCS field '+v)

def adapt(text):
    text='\n'.join(line.partition(';')[0] for line in text.splitlines())+'\n'
    text=re.sub(r'(\$[0-9a-f]+|-?\d+)(?=\(a4(?:\)|,))',lambda m:field(m[0]),text)
    # Indexed slot pointers derive from A4, unlike local frames/control buffers.
    text='\n'.join(line if 'jsr ' in line else re.sub(r'(\$[0-9a-f]+)(?=\(a[2356]\))',lambda m:field(m[0]),line) for line in text.splitlines())+'\n'
    def call(m):
        n=int(m[1],16)
        if n not in CALLS:raise ValueError('unmapped OCS call '+m[0])
        return '$'+format(CALLS[n],'x')+m[2]
    text=re.sub(r'\$([0-9a-f]+)(\(a6\)|,\(sp\))',call,text)
    return text

def source(root):
    pieces=[]
    for name in ('timing_player','player_basis','timing_translation','timing_scene','timing_scene_slots','timing_projectiles'):
        s=english((root/'src'/f'{name}.s').read_text())
        if name=='player_basis':
            s=re.sub(r'(player_basis_offsets: dc.w[^\n]+)',lambda m:re.sub(r'\$[0-9a-f]+',lambda x:field(x[0]),m[0]),s)
        if name=='timing_scene':
            # D2 owns all allocating preparation. Only snapshot/staging remains.
            a=s.index('timing_scene_snapshot:');b=s.index('; Cosmetic regeneration')
            s=s[a:b]+s[s.index('; D0 * fraction'):]
            # Unused full-backup branch/table is removed; selected backup below.
            a=s.index('        else\n        ; Back up all');b=s.index('        endif',a)
            s=s[:a]+s[b:]
            a=s.index('        else\n        lea     timing_scene_saved');b=s.index('        endif',a)
            s=s[:a]+s[b:]
            a=s.index('timing_scene_pose_ranges:');b=s.index('timing_scene_snapshot_ranges:')
            s=s[:a]+s[b:]
            # Snapshot descriptor operands are native offsets too.
            s=re.sub(r'(dc.w[^\n]+)',lambda m:re.sub(r'\$[0-9a-f]+',lambda x:field(x[0]),m[0]),s)
        if name=='timing_scene_slots':
            # No render allocations on OCS. Keep the shared 120-byte record
            # shape, but omit three CD32 attachment fields unused by staging.
            s=s[:s.index('; E:2b648')]+s[s.index('        cnop 0,2'):]
            for off,size in (('3e90','w'),('3fbc','w'),('3b46','b')):
                s=re.sub(r'        move\.'+size+r'  \$'+off+r'\(a[26]\),\(a1\)\+',f'        clr.{size} (a1)+',s)
                s=re.sub(r'        move\.'+size+r'  \(a1\)\+,\$'+off+r'\(a[26]\)',f'        addq.l #{2 if size=="w" else 1},a1',s)
        if name=='timing_projectiles':
            s=s[s.index('projectile_effect_return:'):]
        pieces.append(adapt(s))
    text='\n'.join(pieces)
    # Exact 68000 short-divide fast path for the common velocity domain. Large
    # increments retain the shared signed-long quotient/remainder algorithm.
    text=text.replace('translation_fraction:\n', """translation_fraction:
        cmpi.l #-32768,d0
        blt.w .long_fraction
        cmpi.l #32767,d0
        bgt.w .long_fraction
        muls.w #10,d0
        add.l (a0),d0
        divs.w d7,d0
        move.l d0,d1
        swap d1
        ext.l d1
        move.l d1,(a0)+
        ext.l d0
        rts
.long_fraction:
""")
    text=text.replace('        bsr.w   translation_acceleration', '        bsr.w ocs_acceleration_cached')

    text=text.replace('timing_scene_save_active:\n', 'timing_scene_save_active:\n        lea ocs_projection_saved(pc),a0\n        move.w -11628(a4),(a0)\n')
    text=text.replace('timing_scene_restore_active:\n', 'timing_scene_restore_active:\n        move.w ocs_projection_saved(pc),-11628(a4)\n')
    text+='\nocs_projection_saved: dc.w 0\n'
    text=text.replace('timing_active','ocs_clock_active').replace('timing_hz','ocs_clock_hz').replace('timing_clock','ocs_clock_state').replace('timing_game','game_base')
    # D3 alone leaves this zero; the optional D4 adapter owns intro entry/exit.
    text+='\nintro_active: dc.w 0\n'
    return select('BUFFERED equ 1\nFRAME_STATS equ 0\n'+text,'68000')


def field_source(root):
    text=adapt(english((root/'src/timing_field_shots.s').read_text()))
    text=text.replace('timing_active','ocs_clock_active').replace('timing_game','game_base')
    return select(text,'68000')


def external_source(root):
    text=english((root/'src/timing_external.s').read_text())
    text=re.sub(r'(dc.w[^\n]+)',lambda m:re.sub(r'\$[0-9a-f]+',lambda x:field(x[0]),m[0]),text)
    text=adapt(text).replace('timing_hz','ocs_clock_hz')
    # Placed after exhaust to retain the existing early clock-call reach.
    # The Hz constant is beyond signed-word PC reach in the public payload.
    text=text.replace('move.l  ocs_clock_hz(pc),d7', 'lea timing_external_camera(pc),a0\n        adda.l #ocs_clock_hz-timing_external_camera,a0\n        move.l (a0),d7')
    return select(text,'68000')
