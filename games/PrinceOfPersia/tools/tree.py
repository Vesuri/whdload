#!/usr/bin/env python3
"""Inclusive call tree: tree.py PROF [MIN%] [DEPTH]"""
import sys
from prof import load
red,meta,label=load(sys.argv[1])
print(red.tree(label=label,min_share=float(sys.argv[2] if len(sys.argv)>2 else 1)/100,depth=int(sys.argv[3]) if len(sys.argv)>3 else 6))
