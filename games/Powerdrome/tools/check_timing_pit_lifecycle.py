#!/usr/bin/env python3
"""Audit rescue suspension, interrupted-tail retirement and fresh player entry.

Requires the 19-value PDPIT_EVENT probes, including logical control phase.
Does not certify opponent cadence or general nonlocal exits.
"""
import argparse
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
for root in a.captures:
    prior=entered=returned=retired=None
    last_session=None
    stage='flight'
    visits=modal_samples=modal_opponents=discarded=0
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v=line.split()
        if not v:continue
        if v[0]=='PDSESSION_EVENT':
            last_session=(int(v[1]),int(v[2],16),list(map(int,v[3:])))
        elif v[0]=='PDPIT_EVENT':
            field,off=int(v[1]),int(v[2],16)
            t=list(map(int,v[3:]))
            assert len(t)==19 and last_session[:2]==(field,off)
            s=last_session[2]
            if off==0xce1e:
                assert stage=='flight' and s[8]==s[13]==1
                prior=(s,t);stage='entering'
            elif off==0x103a2:
                assert stage=='entering'
                b,q=prior
                assert t[0]==1 and t[1]==0 and t[2]==q[2]+1
                assert t[8]==q[8]+b[12] and t[9]==q[9]+b[11]
                assert t[10]==q[10]+((b[17]-b[16])&4080)//16
                assert t[12]==q[12]+b[21]-b[22]
                assert all(s[i]==0 for i in (8,9,11,12,13,16,17,18,19,20,21,22))
                discarded+=b[12];entered=t;stage='pit'
            elif stage=='pit' and off==0xce28:
                assert t[0]==0 and t[1]==1 and t[3]==entered[3]+1 and t[4]==entered[4]
                assert t[7]-entered[7]==t[6]-t[5]>0
                assert t[14]==1 and t[15:19]==entered[15:19], 'Private RNG or control phase changed in pit'
                assert all(s[i]==0 for i in (8,9,11,12,13,16,17,18,19,20,21,22))
                returned=t;stage='returning'
            elif stage=='pit':
                assert t[0]==1 and t[15:19]==entered[15:19]
                assert s[8]==s[13]==s[18]==0, 'Player ownership leaked into pit'
                modal_samples+=1
                modal_opponents+=off==0xd56c
            elif stage=='returning':
                assert off!=0xd56c, 'Interrupted flight tail advanced opponents again'
                if off==0xcedc:
                    assert t[1]==1 and s[8]==0
                    retired=s[14]
                elif off==0xca44:
                    assert retired is not None and s[14]==retired, 'Interrupted step was counted complete'
                    assert t[1]==0 and t[13]==returned[13]+1
                    assert s[8]==0 and s[12]==0
                    stage='restarting'
            elif stage=='restarting' and off==0xccee:
                assert s[8]==s[9]==s[12]==s[13]==s[18]==1 and s[11]==0
                assert s[14]==s[10] and s[15]==s[14]+18
                assert s[16]==s[17]==0
                assert t[14]==0 and t[15]==entered[15], 'World random stream reseeded'
                n=t[17]-returned[17]
                assert 0<=n<=2, 'Heat call counter reset at pit reentry'
                seed=returned[16]
                for _ in range(n):seed=(seed*0x7ab7+1)&65535
                assert t[16]==seed, 'Heat random stream reseeded'
                assert t[18]==(entered[18]+1)&65535, 'Control/cooling phase restarted from render count'
                visits+=1;stage='flight'
    assert visits and stage=='flight' and modal_samples
    print(f'{root.name}: {visits} rescue suspension/reentry verified; {discarded} assigned steps explicitly discarded; {modal_samples} inactive pit samples; {modal_opponents} native modal opponent samples (cadence not certified)')
