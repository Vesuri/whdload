#!/usr/bin/env python3
"""Native modal timing arithmetic and simulator loop contracts; no speed claims."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output,require

def check(build,variant,model):
 if variant=='ocs':
  c,sy,_,_=setup(build,model);code,data,s=CODE,DATA,SLAVE
  field=data+0x77fe;hz='ocs_clock_hz'
 else:
  from variants import cd32
  c=Native(ROOT/cd32.GAME,model=model,variant="cd32");code,data,s=CODE,DATA,SLAVE
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(code))
  field=data+0x7f02;hz='timing_hz'
 def call(n,args=b'',regs=None):c.run(s-code+sy[n],args,registers=regs)
 try:
  from modal_source import specification
  rejected=[]
  c.intercept(s+sy['wrong_revision' if variant=='ocs' else 'timing_bad'],lambda:(rejected.append(True),c.return_call()))
  for off,width,_ in specification(variant)[-1]:
   old=c.read(code+off,width);c.write(code+off+width-1,bytes([old[-1]^1]))
   call('modal_guard',regs={1:code});c.write(code+off,old)
  require(len(rejected)==len(specification(variant)[-1]),'modal guard missed a changed site')
  call('modal_guard',regs={1:code});call('modal_install',regs={1:code})
  samples=0
  for rate in (50,60):
   c.write(s+sy[hz],long(rate))
   for elapsed in range(95):
    c.write(field,long(100+elapsed))
    call('modal_run_sample',regs={9:95,4:195})
    want=(elapsed*500//150,elapsed*100//150,elapsed*150//150)
    require(c.get(s+sy['modal_run_tick'])==elapsed*50//150,'running frames')
    require(c.get(s+sy['modal_run_x'])==(-(elapsed*600//150) & 0xfffe),'running scroll')
    require(c.reg(14)==want[1] and c.reg(15)==want[2],'running positions')
    samples+=1
  # Window presentation uses the previous native draw records, not mutable
  # live records. Respawn/RNG/animation stay in the 10 Hz native pass.
  offs=(0x40e2,0x40de,0x411e,0x40e0,-754,2274,-0x2d70) if variant=='ocs' else (0x48f2,0x48ee,0x492e,0x48f0,0x5fa,0x1154,-0x2df2)
  static,nstatic,moving,nmoving,surface,colour,image=tuple(data+0x7ffe+x for x in offs)
  c.write(static,struct.pack('>hhh',12,20,4));c.write(nstatic,word(1))
  c.write(moving,struct.pack('>hhhhhhhh',100,30,7,8,200,40,-11,16));c.write(nmoving,word(2))
  c.write(surface,long(0x180000));c.write(image,long(0x181000));c.write(colour,b'\x01')
  draws=[];publications=[]
  def bitmap():
   draws.append(struct.unpack('>IhhIH',c.read(c.reg(8)+4,14)));c.return_call()
  # Execute the actual native four-rectangle restore, with independent pixels.
  # Clearing stands in for debris overwriting each protected foreground area.
  rects=[]
  for i in range(4):
   base=data+0x7ffe+(0x84c if variant=='cd32' else -0xa0)+i*32
   srcrows=0x190000+i*0x100;dstrows=srcrows+0x20
   src=0x191000+i*0x100;dst=src+0x20
   c.write(base,long(srcrows)+bytes(20)+struct.pack('>hhhh',0,0,3,1))
   c.write(base+128,long(dstrows)+bytes(20)+struct.pack('>hhhh',0,0,3,1))
   c.write(srcrows,long(src)+long(src+4));c.write(dstrows,long(dst)+long(dst+4))
   pixels=bytes(range(8*i+1,8*i+9));c.write(src,pixels);rects.append((dst,pixels))
  def clear():
   for dst,pixels in rects:c.write(dst,bytes(len(pixels)))
   c.return_call()
  def publish():
   for dst,pixels in rects:require(c.read(dst,len(pixels))==pixels,'foreground rectangle overwritten by window')
   publications.append(1);c.return_call()
  c.intercept(s+sy['modal_bar_clear'],clear)
  c.intercept(s+sy['modal_bar_bitmap'],bitmap)
  c.intercept(s+sy['modal_bar_publish'],publish)
  c.intercept(code+(0x2f9a6 if variant=='ocs' else 0x2efe8),bitmap)
  pointers=data+0x7ffe+(0x84 if variant=='ocs' else 0x970)
  assets=data+0x7ffe+(0x47fc if variant=='ocs' else 0x500c)
  for i in range(3):
   c.write(pointers+4*i,long(0x1a0000+16*i));c.write(0x1a0000+16*i,bytes([5+i,9,10,11]))
   c.write(assets+4*i,long(0x181000))
  c.write(data+0x7ffe+(2272 if variant=='ocs' else 4434),word(3))
  call('modal_portraits',long(0x180000))
  require([r[4] for r in draws[-5:]]==[5,0,6,0,7],('foreground fixture',draws))
  bars=0
  for rate in (50,60):
   c.write(s+sy['modal_hz'],word(rate));c.write(s+sy['modal_bar_enabled'],word(1))
   c.write(field,long(100));call('modal_bar_capture')
   c.write(moving,bytes(16)) # Deliberate later respawn must not alter this interval.
   for f in range(1,3):
    draws.clear();c.write(field,long(100+f));before=c.read(data,0xf5b8 if variant=='ocs' else 0xfda0)
    call('modal_bar_between')
    require(c.read(data,len(before))==before,'window presentation mutated game data')
    require([r[1] for r in draws[:3]]==[12,100+int(7*f/3),200+int(-11*f/3)],('window sample',draws))
    require([r[4] for r in draws]==[4,8,16,5,0,6,0,7],'window frame changed')
    bars+=1
   c.write(moving,struct.pack('>hhhhhhhh',100,30,7,8,200,40,-11,16))
  # PAL and NTSC both give 25 cursor updates/second, never a same-field
  # repeat or catch-up burst. Preserve a sampled click until its room owns it.
  polls=[];response={'value':-1}
  def input_poll():
   require(c.get(c.reg(8)+4,4)==0x182000,'room input table ABI')
   polls.append(c.get(field,4));c.return_call(response['value'])
  c.intercept(s+sy['modal_room_native_input'],input_poll)
  c.write(s+sy['modal_room_table'],long(0x182000))
  for rate in (50,60):
   c.write(s+sy['modal_hz'],word(rate))
   c.write(s+sy['modal_room_cursor'],long(0xfffffff0))
   for tick in range(1,21):
    deadline=(0xfffffff0+tick*3)&0xffffffff
    c.write(field,long(deadline));call('modal_room_wait')
    require(c.get(s+sy['modal_room_cursor'],4)==deadline,'room three-field cadence')
   for startfield in (200,0xfffffff0):
    polls.clear();c.write(s+sy['modal_hz'],word(rate))
    c.write(s+sy['modal_room_result'],word(-1))
    c.write(s+sy['modal_room_input_field'],long(startfield))
    c.write(s+sy['modal_room_input_phase'],word(rate))
    for elapsed in range(rate):
     c.write(field,long(startfield+elapsed));call('modal_room_poll');call('modal_room_poll')
     call('modal_room_input');require(c.reg(9)&65535==65535,'unexpected room action')
    require(len(polls)==25,('cursor rate',rate,polls))
    require(all(2<=(b-a)&0xffffffff<=3 for a,b in zip(polls,polls[1:])),'cursor interval')
  response['value']=0;c.write(field,long(500));call('modal_room_poll')
  response['value']=-1;c.write(field,long(514));call('modal_room_poll')
  require(polls[-1]==500,'pending click overwritten')
  call('modal_room_input');require(c.reg(9)&65535==0,'short click lost')
  call('modal_room_input');require(c.reg(9)&65535==65535,'click delivered twice')
  # Input caches text without touching pixels. Every composed image replays
  # it, including unchanged hovers; transparent backgrounds must never fill.
  labels=[]
  context=data+0x7ffe+(-0xc74 if variant=='ocs' else -0x8de)
  labelcontext=data+0x7ffe+(0x1a0 if variant=='ocs' else 0xa8c)
  labelsurface=data+0x7ffe+(0x1b8 if variant=='ocs' else 0xaa4)
  labelcolour=labelsurface-1
  transparent=data+0x7ffe+(0x21fa if variant=='ocs' else 0x2c6c)
  c.write(context,long(0x188000));c.write(labelsurface,long(0x183000))
  c.write(labelcolour,b'\x03');c.write(transparent,b'\x03')
  def label_clear():
   labels.append(('clear',c.get(c.reg(8)+4,4)));c.return_call()
  def label_print():
   labels.append(('print',c.get(c.reg(8)+8,4)));c.return_call()
  def label_reset():
   require(c.get(context,4)==labelcontext,'label context');c.return_call()
  c.intercept(s+sy['modal_label_native_clear'],label_clear)
  c.intercept(s+sy['modal_label_native_print'],label_print)
  c.intercept(s+sy['modal_label_native_reset'],label_reset)
  c.intercept(s+sy['modal_label_native_cursor'],lambda:c.return_call())
  c.write(s+sy['modal_room_polling'],word(1))
  call('modal_label_begin',long(0x183000)+bytes([3,0]))
  call('modal_label_print',long(0x184000)+long(0x185000))
  call('modal_label_end',word(1))
  require(labels==[],'polling modified title pixels')
  for _ in range(8):call('modal_label_replay')
  require(labels==[('print',0x185000)]*8,'transparent persistent title')
  require(c.get(context,4)==0x188000,'text context leaked')
  # Composition, not a new input sample, must restore a lost title.
  labels.clear();call('modal_room_input')
  require(labels==[('print',0x185000)],'room composition missed cached title')
  call('modal_label_print',long(0x184000)+long(0x186000))
  call('modal_label_replay');require(labels[-1]==('print',0x186000),'changed title')
  c.write(s+sy['modal_label_previous'],long(0));labels.clear()
  call('modal_label_replay');require(labels==[],'empty transparent title filled background')
  c.write(labelcolour,b'\x04');call('modal_label_replay')
  require(labels==[('clear',0x183000)],'opaque native clear lost')
  c.write(s+sy['modal_room_polling'],word(0));labels.clear()
  call('modal_label_begin',long(0x183000)+bytes([3,0]))
  call('modal_label_print',long(0x184000)+long(0x186000))
  require(labels==[('clear',0x183000),('print',0x186000)],'original caller changed')
  sims=[]
  clock='ocs_clock_state' if variant=='ocs' else 'timing_clock'
  state={'ticks':0,'pictures':0,'rate':50,'gap':1,'skip':False}
  def start():
   c.write(s+sy[hz],long(state['rate']))
   c.write(s+sy[clock],long(100)+bytes(20)+word(1)+word(0))
   c.write(s+sy['intro_active'],word(1));c.return_call()
  def tick():state['ticks']+=1;c.return_call()
  abort=data+0x7ffe+(-0x707c if variant=='ocs' else -0x7094)
  def finish():
   if state.get('native_abort'):c.write(abort,word(1))
   state['pictures']+=1;c.write(field,long(c.get(field,4)+state['gap']));c.return_call()
  def stop():c.write(s+sy['intro_active'],word(0));c.return_call()
  scales=[]
  def text():
   sp=c.reg(8);scales.append(c.get(sp+12));c.return_call()
  for name,fn in [('intro_start',start),('intro_world',tick),('intro_draw',lambda:c.return_call()),
                  ('intro_finish',finish),('intro_stop',stop),('modal_text',text),
                  ('modal_input',lambda:c.return_call(1 if state['skip'] else 0))]:
   c.intercept(s+sy[name],fn)
  c.write(data+0x7ffe+(-31670 if variant=='ocs' else -31696),long(1))
  for rate in (50,60):
   for gap in (1,3,9):
    for delay,depth in ((0,240),(20,300)):
     state.update(ticks=0,pictures=0,rate=rate,gap=gap,skip=False);scales.clear();c.write(field,long(100))
     call('modal_dispatch',struct.pack('>Ihhhh',0x180000,delay,depth,0,0))
     require(state['ticks']==40,('simulator world count',state))
     require(4*rate<=c.get(field,4)-100<4*rate+gap,('simulator duration',state,c.get(field,4)))
     require(scales and all(0<x<=512 for x in scales),'text scale/ABI')
     if delay==0 and gap==1:require(len(set(scales))>14,'zoom still steps at 10 Hz')
     require(c.get(s+sy['intro_active'])==0,'modal owner leaked')
     sims.append(dict(hz=rate,gap=gap,delay=delay,ticks=state['ticks'],pictures=state['pictures']))
  state.update(ticks=0,pictures=0,rate=50,gap=1,skip=False,native_abort=True)
  c.write(field,long(100));c.write(abort-8,word(0x1234))
  call('modal_dispatch',struct.pack('>Ihhhh',0x180000,0,240,0,0))
  require(state['pictures']==1 and state['ticks']==0,'native abort not observed')
  require(c.get(abort-8)==0x1234 and c.get(abort)==0,'abort damaged adjacent state')
  return dict(model=model,running_samples=samples,installer=True,rejected_sites=len(rejected),bar_samples=bars,foreground_rectangles=4,input_hz=25,hover_label_composition_replay=True,short_click_exactly_once=True,simulator=sims)
 finally:c.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True);a=p.parse_args()
 out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS:',a.variant,'models',len(rows),'modal timing, sampling and guards')
if __name__=='__main__':main()
