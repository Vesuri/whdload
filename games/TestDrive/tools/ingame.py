#!/usr/bin/env python3
"""TD driving view: broad cyan sky, verified against driving and non-driving fixtures."""
import sys
from PIL import Image

def driving(path):
    im=Image.open(path).convert('RGB');w,h=im.size
    def cyan(x,y):
        r,g,b=im.getpixel((int(w*x),int(h*y)))
        return r<110 and 110<g<230 and b>190
    sky=sum(cyan(x,y) for x in (.25,.35,.45,.55,.65) for y in (.18,.23,.28))
    # Cars have different instrument colours; broad sky distinguishes driving
    # from sparse cyan text in title/car/credit screens.
    return sky>=6
if __name__=='__main__':sys.exit(0 if driving(sys.argv[1]) else 1)
