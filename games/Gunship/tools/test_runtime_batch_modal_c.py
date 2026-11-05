"""Run the native modal-continuation fixture through the batch driver."""
s=open(__file__.replace('test_runtime_batch_modal_c.py','test_runtime_modal_resume_c.py')).read()
s=s.replace("   call('scheduler_begin',{1:ptr('SCHEDULER'),9:128,10:8})\n   call('scheduler_next',{1:ptr('SCHEDULER'),2:ptr('RECORD')},1)\n",'')
s=s.replace("call('timing_flight_consume',{1:ptr('CONSUMER'),9:128},3 if n==17 else due)","call('timing_runtime_batch',{1:ARENA,9:128,10:8,11:128},3 if n==17 else 0)")
s=s.replace("    call('timing_runtime_modal_suspend',{1:ARENA})", "    before=c.get(ARENA,size),c.get(low,length)\n    call('timing_runtime_batch',{1:ARENA,9:128,10:8,11:128},3)\n    assert (c.get(ARENA,size),c.get(low,length))==before\n    call('timing_runtime_modal_suspend',{1:ARENA})")
s=s.replace("  call('scheduler_begin',{1:ptr('SCHEDULER'),9:128,10:8})\n  call('scheduler_next',{1:ptr('SCHEDULER'),2:ptr('RECORD')},1)\n  call('timing_flight_consume',{1:ptr('CONSUMER'),9:128})", "  assert word(ptr('BATCH'))==0\n  call('timing_runtime_batch',{1:ARENA,9:128,10:8,11:128})")
assert 'scheduler_next' not in s and 'timing_flight_consume' not in s
exec(s)
