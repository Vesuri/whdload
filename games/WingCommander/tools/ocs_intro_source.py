"""D4 OCS intro adapter. Reuse the owned title loop with explicit OCS ABI."""
from shared_cpu import select
NATIVE=dict(OCS_FLASH=0x15d1c,OCS_INTRO_DRAW=0x2e6,OCS_FINISH=0xb80,
 OCS_INTRO_EXIT=0x1f06e,OCS_INTRO_REPEAT=0x1eeb2)
HOOKS=((0x1ef24,'intro_title',0x4ef9),(0x1effc,'intro_credits_update',0x4eb9),
 (0x1f002,'intro_draw',0x4eb9),(0x1f036,'intro_finish',0x4eb9),
 (0x1f066,'intro_credits_end',0x4ef9),(0x2fa,'intro_flash_draw',0x4eb9))

def source(root):
    shared=(root/'whdload/timing_intro.s').read_text()
    title=shared[shared.index('intro_title:'):shared.index('; Native credit loop')]
    replacements={'timing_game':'game_base','timing_clock':'ocs_clock_state',
     'timing_hz':'ocs_clock_hz','WC_A4_FIELD_CLOCK':'-2048','WC_SCENE_APPROACH':'135',
     'WC_SCENE_DEPARTURE':'235','WC_SCENE_TITLE_UPDATES':'296',
     '-22652(a4)':'-22676(a4)','4438(a4)':'2276(a4)',
     '$13f50(a6)':'$13cc6(a6)',
     '-22256(a4)':'-22292(a4)','-4314(a4)':'-4184(a4)',
     '$2ec98(a6)':'$2f3a0(a6)','$2d746(a6)':'$2d0de(a6)',
     '$1898a(a6)':'$180c4(a6)',
     '#$1fd90':'#$1efb4'}
    for old,new in replacements.items():title=title.replace(old,new)
    return select((root/'whdload/ocs_intro.s').read_text()+'\n'+title,'68000')

def integrate(text):
    # These three wrappers are shared with flight, but intro never enables its
    # input/player flag. Other cinematics keep their original draw preparation.
    for label in ('ocs_clock_scene_draw','ocs_clock_asteroids_draw','ocs_clock_emission'):
        at=text.index(label+':');end=text.index('\nocs_',at+1)
        piece=text[at:end].replace(label+':',label+':\n'+select('        tst.w intro_active(pc)\n        bne.w .intro\n','68000'),1)
        if label.endswith('scene_draw'):
            piece=piece.replace('        jsr OCS_SORT','.intro:\n        jsr OCS_SORT',1)
        elif label.endswith('emission'):
            piece=piece.replace('        move.w 2268(a4),d0','.intro:\n        move.w 2268(a4),d0',1)
        else:piece=piece.replace('.done: rts','.intro:\n.done: rts')
        text=text[:at]+piece+text[end:]
    at=text.index('ocs_prediction_completed:');end=text.index('ocs_prediction_queued:',at)
    piece=text[at:end].replace('        movem.l d0/a0,-(sp)',
      '        movem.l d0/a0,-(sp)\n        lea intro_active(pc),a0\n        tst.w (a0)\n        bne.w .active',1).replace('        movea.l ocs_game_a4(pc),a0','.active:\n        movea.l ocs_game_a4(pc),a0')
    return text[:at]+piece+text[end:]
