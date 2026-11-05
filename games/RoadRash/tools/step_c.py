import os,sys,json,struct
from harness_a import *
# C experiments explicitly opt into the public master switch.
if not any(x.upper().startswith("CUSTOM2=") for x in os.environ.get("WHD_ARGS", "").split()):
 os.environ["WHD_ARGS"] = os.environ.get("WHD_ARGS", "") + " CUSTOM2=1"
s=Session(sys.argv[1]);events=[]
try:
 route(s)
 if os.environ.get('RR_TAPE'):
  tape_path=Path(os.environ.get('RR_TAPE_PATH',ROOT/'tools/fixtures/lap.json'))
  tape=json.loads(tape_path.read_text())
  for target,event,value in tape['events']:
   advance(s,target);events.append(dict(field=target,event=event,value=value,player_flags=hex(rd(s,0xa5dc8,2)),raw_input=hex(read_bytes(s,0xa598c,1)[0])));s.input(event,value)
 else:s.input('JOY2_UP',1);advance(s,800)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);offset=data.find(b'RRCSTEP1');assert offset>=0
 addr=target+offset;b=read_bytes(s,addr,24);cursor,steps,captured,quantum=struct.unpack_from('>4I',b,8);assert captured==int(os.environ.get("RR_CAPTURE","601")),(cursor,steps,captured)
 snap=read_bytes(s,addr+24,0x2e40);(s.out/f'step{captured}.bin').write_bytes(snap)
 hash_addr=addr+24+0x2e40
 header=read_bytes(s,hash_addr,12)
 assert header[:8]==b'RRCHASH2',header
 slots=struct.unpack_from('>I',header,8)[0]
 assert steps<slots,("hash capacity exceeded",steps,slots)
 hashes=read_bytes(s,hash_addr+12,slots*4)
 (s.out/'hashes.bin').write_bytes(hashes)
 view_target=rd(s,0x875ca);view_data=read_bytes(s,view_target,1024);view_offset=view_data.find(b'RRCVIEW1')
 view=None
 if view_offset>=0:
  v=read_bytes(s,view_target+view_offset,80);view=dict(frames=struct.unpack_from('>I',v,8)[0],phase=struct.unpack_from('>I',v,12)[0],histogram=list(struct.unpack_from('>4I',v,16)),positions=list(struct.unpack_from('>12I',v,32)))
 decay=None
 if os.environ.get('RR_DECAY_TEST'):
  decay_target=rd(s,0x8915c);decay_data=read_bytes(s,decay_target,512);decay_offset=decay_data.find(b'RRCDECAY');assert decay_offset>=0
  decay=list(struct.unpack_from('>10i',decay_data,decay_offset+8))
  expected=[]
  for v in [-2147483648,-65536,-32768,-28672,-1,0,1,32767,65536,2147483647]:
   for _ in range(quantum):v-=v*4548//65536
   expected.append(v)
  assert decay==expected,(decay,expected)
 result=dict(decay=decay,hash_slots=slots,events=events,view=view,cursor=cursor,steps=steps,captured=captured,quantum=quantum,provenance=provenance(os.environ['SLAVE'],s),frame_stats=counters(s,stats_address(s)),state_at800=snapshot(s))
 if os.environ.get('RR_EVENTS_TEST'):
  event_target=rd(s,0x8f06c);event_data=read_bytes(s,event_target,1024);event_offset=event_data.find(b'RRCSEV01');assert event_offset>=0
  count,overflow,capacity,record_size=struct.unpack_from('>4I',event_data,event_offset+8)
  assert overflow==0 and 0<count<=capacity and record_size==8,(count,overflow,capacity,record_size)
  data=read_bytes(s,event_target+event_offset+24,count*record_size)
  requests=[dict(field=f,kind=k,value=v) for f,k,v in struct.iter_unpack('>IHH',data)]
  assert all(x['field']<=cursor for x in requests)
  assert requests==sorted(requests,key=lambda x:x['field'])
  result['sound_events']=dict(count=count,overflow=overflow,requests=requests)
 if os.environ.get('RR_STACK_TEST'):
  from stack_probe_c import stack_probe
  result['stack']=stack_probe(s)
 (s.out/'step.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('final.png');print('cursor',cursor,'steps',steps,'position601',struct.unpack_from('>I',snap,0xa5d64-0xa5900)[0],flush=True)
finally:s.quit()
