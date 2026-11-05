#!/usr/bin/env python3
"""Report all whole-data differences plus explicitly decoded simulation quantities."""
import argparse,json,struct,collections
from pathlib import Path
from compare_state import differences
FIELDS={
 'native_field':(-31790,'I'),'pause':(-31736,'h'),'active_fields':(-29930,'H'),'countdown':(-29928,'h'),'period':(-29926,'h'),
 'lap_ticks':(-31424,'H'),'completed_lap_ticks':(-31416,'H'),'lap':(-31422,'h'),'race_tick_counter':(4024,'H'),
 'race_running':(4020,'h'),'start_countdown':(4022,'h'),'status':(-29942,'h'),'inhibit':(-29940,'h'),
 'demo':(3598,'h'),'opponents':(3846,'h'),'speed':(-29944,'H'),'rpm':(-29960,'h'),'gear':(-29818,'h'),
 'fraction':(-30012,'H'),'lateral':(-29976,'h'),'steering':(-29528,'h'),'yaw':(-29522,'h'),'road_curve':(-29516,'h'),
 'raw_joy':(3698,'H'),'consumed_joy':(-20710,'H'),'input_activity':(-20712,'h'),'condition':(3708,'h'),'heat':(-20718,'h'),'rng':(2002,'I'),'render_delta':(3730,'H'),'latched_fields':(-29932,'H')}
FIELDS.update({
 'speed_sum':(-31420,'I'),'max_speed':(-31414,'H'),'statistics_sum':(-31406,'I'),
 'last_lap':(3754,'H'),'lap_display_hold':(3752,'h'),'wheelspin':(-30022,'h'),
 'gear_moving':(-29814,'h'),'clutch':(-29820,'h'),'gear_lever_x':(-29810,'h'),'gear_lever_y':(-29808,'h'),
 'idle_timer':(-20716,'H'),'collision_partner':(-29974,'h'),'collision_frame':(-29970,'h'),
 'spin':(-30610,'h'),'brake_parameter':(-23742,'H'),'grip_parameter':(-23746,'H'),
 'distance_base':(-30004,'I'),'pit_eligible':(-1864,'h'),'finish':(3728,'h')})
def decode(d,m):
 get=lambda off,fmt:struct.unpack_from('>'+fmt,d,0x7ffe+off)[0]
 v={n:get(o,f) for n,(o,f) in FIELDS.items()};v['native_field']-=m['epoch'];origin=get(-29998,'I')
 for n,off in [('segment',-30016),('latched_segment',-30010)]:v[n]=get(off,'I')-origin
 for i in range(10):
  for n,off,fmt,stride in [('AI_segment',6,'I',4),('AI_fraction',46,'H',2),('AI_speed',-34,'H',2),('AI_lateral',-14,'h',2),('AI_cooldown',-154,'h',2)]:
   value=get(off+i*stride,fmt)
   if n=='AI_segment':
    # No-opponent setup leaves a literal sentinel (e.g. $0000ffe3) here.
    # Relocate only actual pointers into the allocated game data hunk; retain
    # all other bits verbatim rather than masking this inactive field.
    pointer=m['data_base']<=value<m['data_base']+0x9364
    v[f'AI_position_pointer_{i}']=pointer
    if pointer:value-=origin
   v[f'{n}_{i}']=value
 v["distance_q8"]=(v["segment"]+v["distance_base"])*256+v["fraction"]
 return v
