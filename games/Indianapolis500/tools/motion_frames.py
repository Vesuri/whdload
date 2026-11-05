#!/usr/bin/env python3
"""Check the frame copies the motion hook rewrites against its private snapshots.
External snapshots (demo, replay) interpolate. Cockpit snapshots extrapolate the camera and
the player's car (alpha 1..2), and opponents that reached last tick's prediction blend from
their current pose to their predicted next pose with alpha - 1.
Also counts car poses the native code built just before the hook that differ from the latest
snapshot: the snapshot must hold what the native frame would draw (replays move only the
external view's nodes, not the car records)."""
import argparse,json,struct,tempfile,os,socket
from pathlib import Path
from state_fields import command
from i500_report import regions
from i500 import SOCK
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
b=a.dump.read_bytes();rr={name:(lo,hi) for lo,hi,name,o in regions(b,a.base)}
lo,hi=rr['slave'];m=b.find(b'I5MO',lo-a.base,hi-a.base)
assert m>=0,'private motion diagnostics missing'
magic=m+a.base;game=rr['game'][0];a.out.mkdir(parents=True,exist_ok=True)
u16=lambda b,o:struct.unpack_from('>H',b,o)[0]
u32=lambda b,o:struct.unpack_from('>I',b,o)[0]
def signed(n):return ((n+32768)&65535)-32768
def lerp(x,y,alpha):return (x+(signed(y-x)*alpha>>14))&65535
def lap(x,y,alpha):
    delta=y-x
    if delta>19800:delta-=39600
    if delta<-19800:delta+=39600
    return (x+(delta if abs(delta)>1000 else delta*alpha>>14))%39600
cockpit=os.environ.get('MOTION_PATH')=='cockpit'
before,after=(0x270,0x276) if cockpit else (0x26d4c,0x26d54)
records=[];shots=[];failures=[];monotonic=0;checked=0;previous=None;followed=0;unfollowed=0
native_poses=0;native_differences=0;moving=0
with tempfile.TemporaryDirectory(prefix='i500-motion-') as temp:
  temp=Path(temp)
  for frame in range(a.frames):
    reply=command(f'''break *{game+before:#x}
continue
delete
dump binary memory {temp}/input-cars.bin {game+0x2326e:#x} {game+0x2326e+398:#x}
break *{game+after:#x}
continue
delete
dump binary memory {temp}/motion.bin {magic:#x} {magic+708:#x}
dump binary memory {temp}/camera.bin {game+0x7a8:#x} {game+0x7ba:#x}
dump binary memory {temp}/cars.bin {game+0x2326e:#x} {game+0x2326e+398:#x}
''')
    inputs=(temp/'input-cars.bin').read_bytes()
    state=(temp/'motion.bin').read_bytes();camera=(temp/'camera.bin').read_bytes();cars=(temp/'cars.bin').read_bytes()
    stamp=u32(state,12);valid=u16(state,18);alpha=u16(state,20);prev=state[24:250];cur=state[250:476]
    nxt=state[476:674];follow=state[674:707];predict=state[707]==1
    row=dict(frame=frame,stamp=stamp,valid=valid,alpha=alpha,path=cur[27],camera=list(struct.unpack('>9H',camera)),cars=[])
    if valid>=2 and cur[26]!=2:
      checked+=1
      if cur[27]!=int(cockpit):failures.append(dict(frame=frame,reason='wrong snapshot source',actual=cur[27]))
      expected=[lerp(u16(prev,2*i),u16(cur,2*i),alpha) for i in range(6)]
      expected += [lap(u16(prev,12),u16(cur,12),alpha),lerp(u16(prev,14),u16(cur,14),alpha),lerp(u16(prev,16),u16(cur,16),alpha)]
      if row['camera']!=expected:failures.append(dict(frame=frame,reason='camera interpolation',expected=expected,actual=row['camera']))
      if previous and stamp==previous['stamp'] and cur==previous['cur']:
        monotonic+=1
        if alpha<previous['alpha']:failures.append(dict(frame=frame,reason='phase moved backwards'))
      count=signed(u16(cars,0))+1
      if not 0<=count<=33:failures.append(dict(frame=frame,reason='car count',count=count));count=0
      track=lap(u16(prev,18),u16(cur,18),alpha)
      for n in range(count):
        off=2+n*12;ptr=u32(cars,off+2);index=(ptr-game-0x22758)//86
        if (ptr-game-0x22758)%86 or not 0<=index<33:failures.append(dict(frame=frame,reason='car pointer'));continue
        pose=[u16(cars,off+i) for i in (6,8,10)];offset=28+index*6
        native_pose=[u16(inputs,off+i) for i in (6,8,10)]
        native_poses+=1;native_differences+=native_pose!=[u16(cur,offset+i) for i in (0,2,4)]
        moving+=[u16(prev,offset+i) for i in (0,2,4)]!=[u16(cur,offset+i) for i in (0,2,4)]
        if predict and index and follow[index]:
          followed+=1;n=index*6;fraction=alpha-16384
          expected=[lap(u16(cur,offset),u16(nxt,n),fraction),lerp(u16(cur,offset+2),u16(nxt,n+2),fraction),lerp(u16(cur,offset+4),u16(nxt,n+4),fraction)]
        else:
          unfollowed+=bool(predict and index)
          expected=[lap(u16(prev,offset),u16(cur,offset),alpha),lerp(u16(prev,offset+2),u16(cur,offset+2),alpha),lerp(u16(prev,offset+4),u16(cur,offset+4),alpha)]
        if pose!=expected:failures.append(dict(frame=frame,reason='car interpolation',index=index,expected=expected,actual=pose))
        distance=track-pose[0]
        if distance>=19800:distance-=39600
        if distance<-19800:distance+=39600
        native=signed(u16(inputs,off))
        native_delta=u16(cur,18)-u16(cur,offset)
        if native_delta>=19800:native_delta-=39600
        if native_delta<-19800:native_delta+=39600
        bias=signed(native-native_delta)
        actual=signed(u16(cars,off))
        if actual!=signed(distance+bias):failures.append(dict(frame=frame,reason='car distance',index=index,expected=signed(distance+bias),actual=actual,bias=bias))
        row['cars'].append(dict(index=index,pose=pose,distance=actual,native_distance=native,bias=bias))
      previous=dict(stamp=stamp,alpha=alpha,cur=cur)
    records.append(row)
    if failures:break
  # Screenshots have a separate swap loop: a one-field capture must not
  # skip the frame-copy breakpoint used for the mathematical checks above.
  for frame in range(int(os.environ.get('MOTION_SHOTS','0'))):
    command(f'break *{game+0xb2e2:#x}\ncontinue\ndelete\ndump binary memory {temp}/shot-camera.bin {game+0x7a8:#x} {game+0x7ba:#x}')
    shot=a.out/f'{frame:03d}.png'
    with socket.socket(socket.AF_UNIX) as connection:
      connection.connect(SOCK);connection.sendall(f'shot {shot.resolve()}'.encode())
      reply=b''
      while chunk:=connection.recv(65536):reply+=chunk
    assert shot.exists(),reply.decode()
    shots.append(dict(screenshot=shot.name,camera=list(struct.unpack('>9H',(temp/'shot-camera.bin').read_bytes()))))
(a.out/'motion.json').write_text(json.dumps(dict(frames=records,checked_frames=checked,monotonic_pairs=monotonic,predicted_cars=followed,extrapolated_opponents=unfollowed,native_poses=native_poses,native_differences=native_differences,moving_poses=moving,shots=shots,failures=failures),indent=2)+'\n')
print(f'{len(records)} motion frames, {monotonic} consecutive pairs within a tick, {len(failures)} differences')
if followed or unfollowed:print(f'opponent poses: {followed} predicted, {unfollowed} extrapolated')
print(f'car poses: {native_poses}, {moving} moved since the previous tick, {native_differences} native inputs differ from the latest snapshot')
if not checked:raise SystemExit('no interpolated frames were observed')
if failures:raise SystemExit('motion-copy verification failed')
