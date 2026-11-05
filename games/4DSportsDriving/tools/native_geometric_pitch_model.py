"""Offline hypothesis: use native absolute geometric pitch reconstruction at50Hz.
No rate interpolation or20Hz stepping. Only replace Q8 change accumulation with
the original endpoint-axis lookup and its original abs(pitch)<2 deadband.
"""
from contact_body_predictor import body
from native_contact_response import rotate,atan_native
from airborne_pitch_predictor import axis

def control(entry,build,rows,state):return body(entry,build,rows)
def solve(entry,build,rows,state):
 out=body(entry,build,rows)
 basis=[[a+b for a,b in zip(end['position'],rotate([0,384+su['returned'],0],entry[4:13]))]for end,su in zip(out['wheels'],out['suspensions'])]
 pitch=atan_native(*axis(basis))-256
 out['pitch']=0 if abs(pitch)<2 else pitch
 out['pitch_carry']=0
 return out
