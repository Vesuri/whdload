#!/usr/bin/env python3
"""Recognise the GPC cockpit: blue sky, green verge, dark wheel and white gauges.
Coordinates are relative to the active 320x200 image in Barto's 768x576 screenshot.
"""
import sys
from PIL import Image

def ingame(path):
    im=Image.open(path).convert('RGB'); w,h=im.size
    def near(x,y,c):
        return max(abs(a-b) for a,b in zip(im.getpixel((int(w*x),int(h*y))),c)) < 35
    yellow=sum(1 for red,green,blue in im.crop((int(w*.30),int(h*.55),int(w*.60),int(h*.73))).getdata() if red>180 and green>180 and blue<60)
    return near(.52,.20,(17,170,255)) and near(.19,.35,(0,204,0)) and yellow>30

if __name__=='__main__': raise SystemExit(0 if ingame(sys.argv[1]) else 1)
