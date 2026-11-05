"""Terminal reset may change only private prediction validity and player history."""
source=open(__file__.replace('test_runtime_retire_c.py','test_timing_runtime_c.py')).read()
exec(source.split("c.put(ARENA-16,")[0].split('# Loader-facing lookup')[0])
runs=[]
for rate in (50,60):
 c.put(ARENA-16,b'\xa5'*(size+32));c.put(p+24,bytes(1));c.put(h[2]+0x0c,bytes(4));prepare(rate)
 # Prepared inactive arena satisfies the helper's suspension contract.
 # Force stale content so zeroed allocator bytes cannot make this pass.
 ranges=[(sym('RT_ENDPOINT'),sym('EP_SIZE')),(sym('RT_FORECAST')+sym('RF_TAPE'),8),(sym('RT_FORECAST')+sym('RF_EVENT'),4),(sym('RT_FORECAST')+sym('RF_ACTOR_SAFE'),2),(sym('RT_FORECAST')+sym('RF_PRESENT_SAFE'),2)]+[(sym('RT_'+block)+sym(off),2) for block,off in [('PLAYER_CACHE','PC_VALID'),('ACTOR_PRESENT','AC_VALID'),('RELEASE_PRESENT','AC_VALID'),('SCRIPT_PRESENT','SPC_VALID')]]
 for off,n in ranges:c.put(ARENA+off,b'\x55'*n)
 before=bytearray(c.get(ARENA,size));native=c.get(low,length)
 expected=before[:]
 for off,n in ranges:expected[off:off+n]=bytes(n)
 call('timing_runtime_retire',{1:ARENA})
 assert c.get(ARENA,size)==expected
 assert c.get(low,length)==native
 assert c.get(ARENA-16,16)==c.get(ARENA+size,16)==b'\xa5'*16
 # A repeated terminal retirement must not touch counters or native state.
 call('timing_runtime_retire',{1:ARENA})
 assert c.get(ARENA,size)==expected and c.get(low,length)==native
 runs.append(rate)
print(json.dumps(dict(status='passed',rates=runs,exact_write_ranges=True,native_unchanged=True,guards=True,idempotent=True,registers_preserved=True)))
c.close()
