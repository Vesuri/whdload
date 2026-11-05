# Audited transformations applied by build_step5_verify_split_v2.py.
def original_body(name):
 import re
 m=re.search(r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_][A-Za-z_0-9]*:)',source,re.S|re.M);assert m,name
 return m[1]
def drop(s,part):
 assert part in s,part
 return s.replace(part,'',1)
alternate('velocity_record',' lea (velocity_scratch.l,pc),a4\n rts\n')
for name,parts in {
 'velocity_project':[
 ' move.w $32fbc,(a4)\n', ' move.w 14(a6),4(a4)\n',
 ' move.w -14(a6),8(a4)\n move.w -16(a6),10(a4)\n move.w $32f94,12(a4)\n move.w $32f96,14(a4)\n',
 ' move.l velocity_records_count(pc),d3\n lsl.l #2,d3\n lea (velocity_target_speeds,pc),a0\n move.l d0,(a0,d3.l)\n'],
 'velocity_returned':[
 ' move.w d7,6(a4)\n move.w $32f94,16(a4)\n move.w $32f96,18(a4)\n',
 ' move.l velocity_records_count(pc),d0\n lsl.l #3,d0\n lea (speed_feedback_records,pc),a2\n adda.l d0,a2\n move.l (a1),(a2)\n move.w 4(a1),4(a2)\n clr.w 6(a2)\n',
 ' move.w #1,6(a2)\n',
 ' move.w (a0),16(a4)\n move.w 4(a0),18(a4)\n',
 ' move.w d0,6(a4)\n'],
 'fine_advance':[
 ' ; Record input before changing the independent axis states.\n move.l fine_steps(pc),d0\n cmpi.l #800,d0\n bhs.w fine_record_overflow\n lsl.l #5,d0\n lea (fine_records.l,pc),a4\n adda.l d0,a4\n move.w $32fbc,(a4)\n clr.w 2(a4)\n move.w $32f94,4(a4)\n move.w $32f96,6(a4)\n move.l (a0),8(a4)\n move.l 4(a0),12(a4)\n move.l 8(a0),16(a4)\n',
 ' move.l fine_steps(pc),d0\n mulu.w #12,d0\n lea (position_velocity_inputs.l,pc),a1\n adda.l d0,a1\n move.l (a2),(a1)\n move.l 4(a2),4(a1)\n move.l 8(a2),8(a1)\n',
 ' move.w d1,2(a4)\n',
 ' move.l (a0),20(a4)\n move.l 4(a0),24(a4)\n move.l 8(a0),28(a4)\n'],
 'heading_step':[
 ' move.l heading_steps(pc),d0\n cmpi.l #1600,d0\n bhs.w fine_fault\n mulu.w #24,d0\n lea (heading_records.l,pc),a4\n adda.l d0,a4\n move.w $32fbc,(a4)\n move.w d5,2(a4)\n move.l d4,4(a4)\n',
 ' move.l (a0),8(a4)\n move.w 4(a0),12(a4)\n clr.w 14(a4)\n',
 ' move.l (a0),16(a4)\n move.w 4(a0),20(a4)\n move.w d1,22(a4)\n'],
 'steering_sample':[
 ' move.l steering_samples(pc),d0\n cmpi.l #800,d0\n bhs.w velocity_fault\n mulu.w #20,d0\n lea (steering_records.l,pc),a4\n adda.l d0,a4\n move.l ticks(pc),d3\n move.l d3,(a4)\n move.w $32fbc,4(a4)\n move.w d4,6(a4)\n move.l 12(a0),12(a4)\n sub.l 12(a0),d3\n move.l d3,16(a4)\n',
 ' move.w d2,8(a4)\n move.w d0,10(a4)\n']
}.items():
 lean=original_body(name)
 for part in parts:lean=drop(lean,part)
 alternate(name,lean)
# Diagnostic-only validation of the integer views. No native output is produced.
alternate('velocity_check',' rts\n')
# Calls to pure diagnostics are excluded too: no empty-call trampoline cost.
for name in ('events_after','clocks_after','counters_after','boost_after','recovery_contact_before','recovery_contact_after'):
 pattern=r'(?m)^ bsr\.w '+name+r'\n'
 source=re.sub(pattern,lambda m:' IFD VERIFY\n'+m[0]+' ENDC\n',source)
# Statistics are not simulation serials/phase/debt. Keep the latter always live.
stats=set('velocity_loads velocity_stores velocity_rotations velocity_projects velocity_raws velocity_records_count velocity_cold_writes velocity_swaps velocity_work_resets velocity_clamps velocity_impulses velocity_offroads speed_records_count speed_loads speed_stores speed_cold_writes speed_swaps bridge_array_resets bridge_snapshots bridge_restores bridge_contacts bridge_loads bridge_stores bridge_rotations bridge_resets fine_steps heading_steps heading_zeroes heading_resets heading_assignments steering_samples steering_resets wear_samples wear_resets events_samples events_rng_calls events_pulses clocks_samples counters_samples fuel_samples fuel_resets boost_samples recovery_contacts recovery_samples'.split())
pattern=r'(?m)^ lea \(?([A-Za-z_][\w]*)(?:\.l)?[,\(]pc\),a([0-6])\n addq\.l #1,\(a\2\)\n'
stat_sites=[]
def guard_stat(m):
 if m[1] not in stats:return m[0]
 stat_sites.append(m[1]);return ' IFD VERIFY\n'+m[0]+' ENDC\n'
source=re.sub(pattern,guard_stat,source)
# Guard pure assertion branches, retaining arithmetic which supplies native data.
# Their predicate instructions can be optimized separately; removing the branch
# keeps flags/register behavior unchanged even where a result is shared.
fault_sites=[]
pattern=r'(?m)^ b(?:ne|hi|hs|mi|vs|lo)\.[bw] (?:velocity_fault(?:_x|_z)?|fine_fault|fine_record_overflow)\n'
def guard_fault(m):
 fault_sites.append(m[0].strip());return ' IFD VERIFY\n'+m[0]+' ENDC\n'
source=re.sub(pattern,guard_fault,source)
# VBL/tick accounting stays observable for this diagnostic; it is not a stat.
# Reuse the first 80 bytes as working memory; no record history is produced.
source=source.replace('velocity_records: ds.b 64000',' IFND VERIFY\nvelocity_scratch equ velocity_records\n ENDC\nvelocity_records: ds.b 64000',1)
# Unused observer-only routines and RNG-counting trampoline disappear in lean.
for name in ('events_record','clocks_record','clocks_pointer','counters_record','counters_value','boost_record','recovery_record','recovery_contact_record'):
 alternate(name,' rts\n')
alternate('events_24eec',' dc.w $4e56,$fffe,$2079,$0002,$4fd4\n jmp $24ef6\n')
# Timer trace is VERIFY-only; the actual elapsed/debt context remains operational.
for part in [
 ' bsr.w schedule_record\n move.l FF1T_FIELDS(a0),(a4)\n move.l d2,8(a4)\n move.l d1,12(a4)\n move.l ticks(pc),24(a4)\n',
 ' bsr.w schedule_record\n',
 ' move.l FF1T_FIELDS(a0),4(a4)\n',
 ' move.l d0,28(a4)\n',
 ' bsr.w FF1TimeDue\n move.l d2,16(a4)\n move.l d1,20(a4)\n lea schedule_completed(pc),a1\n addq.l #1,(a1)\n']:
 assert part in source,part
 source=source.replace(part,' IFD VERIFY\n'+part+' ENDC\n',1)
source=source.replace('schedule_completed: dc.l 0',' IFD VERIFY\nschedule_completed: dc.l 0\n ELSE\nschedule_completed equ schedule_context+FF1T_TICKS\n ENDC')
# No trace arrays in the untraced variant. Retain named zero-length boundaries
# for the debugger and the same include interface, plus the 80-byte workspace.
trace_labels='velocity_records velocity_target_speeds speed_records speed_feedback_records fine_records heading_records position_velocity_inputs steering_records wear_records events_records clocks_records counters_records fuel_records boost_records recovery_contact_records recovery_records schedule_records'.split()
for name in trace_labels:
 pattern=r'(?m)^'+name+r': ds\.[bl] \d+$'
 m=re.search(pattern,source);assert m,name
 lean=name+': ds.b '+('80' if name=='velocity_records' else '0')
 source=source[:m.start()]+' IFD VERIFY\n'+m[0]+'\n ELSE\n'+lean+'\n ENDC'+source[m.end():]
# A4 addresses arithmetic workspace in lean; identify that accurately in profiles.
source=source.replace('velocity_record:\n IFD VERIFY',' IFD VERIFY\nvelocity_record:\n ELSE\nvelocity_workspace:\n ENDC\n IFD VERIFY',1)
source=re.sub(r'(?m)^ bsr.w velocity_record\n', ' IFD VERIFY\n bsr.w velocity_record\n ELSE\n bsr.w velocity_workspace\n ENDC\n', source)
# Native-context range and consistency assertions, not helper error contracts.
for name in ('bridge_context','bridge_rotate','bridge_contact'):
 body=original_body(name)
 body=re.sub(r'(?m)^ b(?:hi|ne)\.b \.bad\n',lambda m:' IFD VERIFY\n'+m[0]+' ENDC\n',body)
 pattern=r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_][A-Za-z_0-9]*:)'
 m=re.search(pattern,source,re.S|re.M)
 source=source[:m.start()]+name+':\n'+body+source[m.end():]
source=source.replace(' cmp.w events_pulse(pc),d0\n bne.w schedule_bad\n',' IFD VERIFY\n cmp.w events_pulse(pc),d0\n bne.w schedule_bad\n ENDC\n')
# Signed range checks and pointer assertions are diagnostics too.
source=re.sub(r'(?m)^ b(?:lt|gt)\.w velocity_fault\n|^ b(?:hi|ne)\.w bridge_pointer_bad\n',lambda m:' IFD VERIFY\n'+m[0]+' ENDC\n',source)
