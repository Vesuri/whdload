"""P13D1 responsibility-to-native-test map; all addresses are OCS hunk offsets.

Scope and named excluded scenes are in docs/internals.md, P13D1. Tests establish
local semantics, not whole-game determinism or physical interrupt delivery.
"""
# id: (primary code owner, data owners, native report paths, excluded scene IDs)
FINDINGS = {
    'FR-01': (0x7e2c, (0x8928,0x94fa), ('schedules.10Hz.position_fixed8','extended.50Hz.accelerated_position_fixed8','ocs_owners.units'), ('X1',)),
    'FR-02': (0x79fc, (0x8d06,0x8d86,0x8e06), ('extended.10Hz.orientation_forward','schedules.50Hz.angular_decay'), ('X1',)),
    'FR-03': (0xc8ee, (0x9cda,), ('schedules.10Hz.fuel',), ('X1',)),
    'FR-04': (0x7b86, (0xb102,), ('schedules.50Hz.afterburner_timer',), ('X1',)),
    'FR-05': (0x741e, (0x8c54,0xa9b8), ('schedules.10Hz.object_life','extended.50Hz.despawn_size','ocs_owners.gun_reload_is_not_reset'), ('X1',)),
    'FR-06': (0x7550, (0xb096,), ('schedules.boundary_checks.signed_byte_lifetime','extended.10to50.missile_expiry_seconds'), ('X1',)),
    'FR-07': (0xc91a, (0x88da,0x8cd4,0x9d02,0xb628), ('schedules.10Hz.shields','schedules.50Hz.gun_energy'), ('X1',)),
    'FR-08': (0xa320, (0xb65a,0xb472), ('extended.10Hz.ship_death_delay','extended.50Hz.collision_cooldown'), ('X1',)),
    'FR-09': (0x873c, (0xb8b6,0xb8c0,0xb7de,0x6f9a), ('schedules.50Hz.ai_decision_opportunities','extended.10Hz.ai_stagger_delay','schedules.10Hz.rng'), ('X1',)),
    'FR-10': (0x13ad6, (0x38c,0xb0e0,0xb860,0xb876), ('extended.10Hz.action_writer_sites','extended.boundaries.action_reset','dispatch.targets'), ('X1',)),
    'FR-11': (0xd1f0, (0x3890,0xb8ca), ('extended.10Hz.lock_countdown','extended.10Hz.contact_hold','ocs_owners.target_draw_mask'), ('X1','X6')),
    'FR-12': (0x156e6, (0x8928,0x8e8c,0x9288), ('schedules.boundary_checks.point_overlap',), ('X1',)),
    'FR-13': (0x115f2, (0xb0fe,0xa1f6), ('extended.10Hz.proximity_samples_inside','extended.50Hz.proximity_samples_inside'), ('X1',)),
    'FR-14': (0x2800a, (0xb664,0xb6e4,0x5426), ('schedules.50Hz.effect_script_advances','extended.boundaries.effect_opcodes'), ('X1','X2')),
    'FR-15': (0x636a, (0x88de,), ('extended.50Hz.periodic_opportunities.4',), ('X1',)),
    'FR-16': (0x2018, (0x9e64,0xa8b8,0xbbc2,0x9e7e), ('schedules.10Hz.message_remaining','extended.50Hz.cockpit_selection','schedules.10Hz.six_byte_timers','extended.50Hz.comms_rng','ocs_owners.fault_poll_rng','ocs_owners.simulator_score_time','ocs_owners.simulator_exit_once'), ('X1','X5')),
    'FR-17': (0x276, (0x88da,0x88dc), ('extended.50Hz.periodic_opportunities.32','extended.50Hz.periodic_opportunities.16'), ('X1',)),
    'FR-18': (0x6584, (0xb03e,0x8cce,0xb880), ('extended.10Hz.camera_state_wait','extended.10Hz.demo_script_wait','extended.10Hz.class1_elapsed','extended.10Hz.class1_countdown'), ('X2',)),
    'FR-19': (0x18d14, (0x7808,0x780a,0xbed2,0x8e88), ('ocs_owners.keyboard_queue_wrap','ocs_owners.joystick_edge_consumption','ocs_owners.joystick_field_timers','ocs_owners.held_axis_and_release'), ('X3','X4','X5')),
    'FR-20': (0xd9e, (0x77fe,0xbf58,0xaa,0xa8), ('extended.boundaries.vbl_deadline_remaining','extended.10Hz.landing_size','ocs_owners.simulator_exit_once'), ('X1','X2','X5')),
    'FR-21': (0x342a2, (0x77fe,0x7802,0x5228,0x522a), ('ocs_owners.field_wrap_and_countdown','extended.10Hz.vbl_counter','ocs_owners.audio_field_accumulator'), ('X3',)),
    'FR-22': (0xb0fe, (0x88b4,), ('extended.boundaries.event_counts',), ('X1',)),
    'FR-23': (0x12466, (0xb860,0x8c54,0xb096), ('extended.boundaries.word_wrap','extended.boundaries.life_sentinel','extended.boundaries.high_bit_shift_probe'), ('X7',)),
}


def coverage(results):
    assert set(FINDINGS)=={f'FR-{i:02d}' for i in range(1,24)}
    rows={}
    for key,(owner,fields,paths,excluded) in FINDINGS.items():
        assert paths
        for path in paths:
            value=results
            for part in path.split('.'):value=value[part]
            assert value is not None
        rows[key]=dict(code_hunk=f'{owner:05x}',code_file=f'{owner+0x2c:05x}',
            data_hunk=[f'{x:04x}' for x in fields],tested=paths,excluded_scenes=excluded)
    return rows
