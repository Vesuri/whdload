#!/usr/bin/env python3
"""Ensure the paired-window gate rejects corrupt counts and changed gameplay."""
import check_blitter as c
original_read=c.read
for mode in ['fps','count']:
 def changed(p):
  r=original_read(p)
  if p.name=='swaps.json':r['window_fps' if mode=='fps' else 'presentations']+=1
  return r
 c.read=changed
 try:c.check()
 except AssertionError:pass
 else:raise AssertionError('accepted corrupt '+mode)
c.read=original_read
original_state=c.state
def changed_state(p,m):
 r=original_state(p,m)
 if '-on' in str(p):r['pos']+=1
 return r
c.state=changed_state
try:c.check()
except AssertionError:pass
else:raise AssertionError('accepted changed gameplay')
print('PASS: rejected inconsistent FPS, corrupt counts and changed gameplay')
