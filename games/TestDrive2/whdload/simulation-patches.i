    ; Higher-rate simulation, duel v1 only. Off restores the original game.
    PL_IFC2
    PL_PS  $05a4c,sim_start
    PL_PSS $05a5a,sim_begin,2
    PL_L   $05bea,$70034e71    ; deadline comparison: moveq #3,d0; nop
    PL_L   $05c0c,$70034e71    ; deadline advance: moveq #3,d0; nop
    PL_W   $0b29e,$ee88        ; player motion: speed /128 (was /64)
    PL_PSS $0a8e6,sim_speed_add,2
    PL_W   $0a7e0,$ea49        ; clutch RPM decay /32 (was /16)
    PL_L   $0a7f8,176128       ; clutch braking, original 352256 /2
    PL_L   $0a802,425984       ; assisted clutch braking, 851968 /2
    PL_L   $0a82a,16384        ; neutral drag, 32768 /2
    PL_W   $0a838,350          ; free RPM rise, 700 /2
    PL_L   $0a854,16384        ; fuel-out drag, 32768 /2
    PL_L   $0a868,139264       ; braking, 278528 /2
    PL_L   $0a872,393216       ; assisted braking, 786432 /2
    PL_L   $0a910,44032        ; tyre scrub, 88064 /2
    PL_W   $0b0e4,$e840        ; heading relaxation /16 (was /8)
    PL_W   $0b0ee,$e640        ; yaw relaxation /8 (was /4)
    PL_PSS $0b1a2,sim_yaw_add,2
    PL_W   $0b2d4,$720a        ; auto-centre lane at 10 (was 20)
    PL_W   $0b2fa,$720a        ; return to road at 10 (was 20)
    PL_W   $0aee0,$e649        ; overheat cooling /8 (was /4)
    PL_PSS $0aeee,sim_heat_add,2
    PL_PS  $0adf8,sim_dashboard
    PL_PSS $0dd52,sim_ai_accel,2
    PL_L   $0dcd6,3072         ; AI stopping deceleration, 6144 /2
    PL_L   $0dd18,768          ; pursuit braking, 1536 /2
    PL_L   $0dd30,1216         ; normal AI braking, 2432 /2
    PL_L   $0de30,512          ; AI curve braking, 1024 /2
    PL_PSS $0de36,sim_ai_motion,2
    PL_PS  $0ddce,sim_ai_lane
    PL_PS  $0e080,sim_ai_lane
    PL_L   $0def4,768          ; police braking, 1536 /2
    PL_L   $0df30,768          ; police restart acceleration, 1536 /2
    PL_PS  $0df54,sim_police_return_lane
    PL_PSS $0e0f2,sim_traffic_forward,2
    PL_PSS $0e1b0,sim_traffic_oncoming,2
    PL_PSS $0d77a,sim_crash_timer,4
    PL_PSS $0df16,sim_police_timer,4
    PL_PSS $0df36,sim_police_time_motion,6
    PL_PSS $0e016,sim_police_time_read,2
    PL_PS  $0e062,sim_police_limit_branch
    PL_PS  $0e06e,sim_police_limit
    PL_PSS $0d216,sim_gear_timer,4
    PL_PS  $08bee,sim_verge_low
    PL_PS  $08bfa,sim_verge_high
    PL_PS  $08c30,sim_verge_low
    PL_PS  $08c3c,sim_verge_high
    PL_W   $091b8,$ec88        ; distance-driven effect phase /64 (was /32)
    PL_PS  $05c74,sim_overheat_check
    PL_PS  $05c80,sim_crash_check
    PL_PS  $06510,sim_dashboard_draw
    PL_PSS $05b8c,sim_player_time,2
    PL_PS  $05bc0,sim_opponent_sum
    PL_NOP $05bc6,4            ; advance opponent time at shared entry below
    PL_PS  $05bca,sim_opponent_time
    PL_NOP $08cd0,32           ; phase accumulation now in simulation
    PL_P   $08d94,sim_draw_event
    PL_W   $0e9f0,$7200        ; gameplay RNG excludes beam-position entropy
    PL_NOP $0e9f2,4
    PL_ENDIF
