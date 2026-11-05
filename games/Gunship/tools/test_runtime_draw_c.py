"""One-draw handoff, binding admission and records arriving during rendering."""
__file__=__file__.replace('test_runtime_draw_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
draws=0;inject=False;seen=[]
@CODE
def drawn(handle,a,n,user):
 global draws,inject
 draws+=1
 assert c.rr(5)==h[6] and word(ptr('VIEW_PHASE'))==1
 assert c.get(h[4],54)==c.get(h[5]+10,54)==c.get(h[6]+0x3904,54)
 seen.append((long(ptr('SCHEDULER')+sym('TS_STEPS')),c.get(p,86)))
 if inject:
  inject=False
  history=ptr('HISTORY');index=word(history);record=bytearray(c.get(SAMPLE,40))
  field=long(history+16)+1;struct.pack_into('>I',record,0,field)
  c.put(history+20+(index%128)*40,record);c.put(history+16,struct.pack('>I',field));c.put(history,struct.pack('>H',(index+1)&65535))
dh=C.c_size_t();entry=h[0]+0x5c04;ok(u.uc_hook_add(c.h,C.byref(dh),1<<2,drawn,None,entry,entry))
for rate in (50,60):
 setup(rate);assert word(ptr('DRAW_READY'))==0 and long(ptr('DRAW_ENTRY'))==entry
 # No draw can begin until installation has completed.
 before=c.get(ARENA,size),c.get(low,length);call('timing_runtime_draw',{1:ARENA},0xfffffffd);assert (c.get(ARENA,size),c.get(low,length))==before
 c.put(ptr('DRAW_READY'),b'\0\1');c.put(entry,bytes.fromhex('4e75'))
 for field in range(1,41,2):
  c.put(SAMPLE,struct.pack('>6IHhhHII',1000+field,0,0,0,0,500,8,0,0,0,10,field))
  call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1);assert pump()==0
  steps=long(ptr('SCHEDULER')+sym('TS_STEPS'));read=word(ptr('HISTORY')+2);before_player=c.get(p,86);previous=draws;inject=True
  call('timing_runtime_draw',{1:ARENA})
  assert draws==previous+1 and not inject and c.get(p,86)==before_player
  assert word(ptr('HISTORY')+2)==read and long(ptr('SCHEDULER')+sym('TS_STEPS'))==steps
  assert (word(ptr('HISTORY'))-read)&65535==1
  assert pump()==0 and long(ptr('SCHEDULER')+sym('TS_STEPS'))==steps+1
 # Invalid bindings/admission must not publish or call native drawing.
 for addr,data in [(ptr('DRAW_ENTRY'),struct.pack('>I',entry+2)),(ptr('DRAW_READY'),b'\0\2'),(ptr('CAPTURE_OWNER'),bytes(2)),(ptr('BATCH'),b'\0\1'),(ptr('VIEW_PHASE'),b'\0\2')]:
  old=c.get(addr,len(data));c.put(addr,data);before=c.get(ARENA,size),c.get(low,length);previous=draws
  call('timing_runtime_draw',{1:ARENA},0xfffffffd)
  assert draws==previous and (c.get(ARENA,size),c.get(low,length))==before;c.put(addr,old)
print(json.dumps(dict(status='passed',draws=draws,fields=80,concurrent_publications_deferred=40,invalid_admissions=12,native_draw_stubbed=True)))
c.close()
