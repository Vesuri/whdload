"""Discard a suspended batch's undelivered snapshot before a fresh epoch."""
__file__=__file__.replace('test_boundary_backlog_c.py','test_runtime_boundary_finish_c.py')
fixture=open(__file__).read();exec(fixture.split('cases=0')[0])
setup(50)
for n in range(1,4):publish(n,0x42 if n==1 else 0)
assert pump()==2 and word(ptr('SCHEDULER')+16)==2
ui();assert long(ptr('HISTORY')+12)==2
finish(0);assert word(ptr('SCHEDULER')+16)==0 and long(ptr('SCHEDULER')+32)==1
rebase();assert long(ptr('SCHEDULER')+32)==2 and long(ptr('SCHEDULER')+36)==0
print(json.dumps(dict(status='passed',discarded_snapshot_fields=2,only_retained_field_completed=True,fresh_epoch_accepted=True)));c.close()
