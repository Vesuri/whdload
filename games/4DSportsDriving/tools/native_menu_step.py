#!/usr/bin/env python3
"""Advance arbitrary original/runtime UI through native keyboard and PAL fields."""
import os,sys
from pathlib import Path
from profile_window import command,ROOT
cap=(ROOT/os.environ['RUNTIME_CAPTURE']).resolve();assert cap.is_relative_to(ROOT/'tmp')
def fields(n):
 while n:
  k=min(n,100);out=command(f'gdb monitor profile {k} "" "{cap}/step.bin"');assert "error" not in out.lower(),out;n-=k
command('stop')
for token in sys.argv[1:]:
 if token.startswith('wait:'):fields(int(token[5:]));continue
 raw=int(token,16);command(f'gdb monitor key {raw:x} 1');fields(10);command(f'gdb monitor key {raw:x} 0');fields(10)
