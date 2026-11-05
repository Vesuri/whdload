#!/usr/bin/env python3
"""Exact interval audit of five 50 Hz drag steps against two native updates.

For each speed, partition ALL 65536 initial carries at every quotient boundary.
Within a partition the speed is constant and carry = initial_carry + offset.
This covers 4*65536*65536 initial states without enumerating each separately.
"""
import json
from decimal import Decimal, getcontext, ROUND_HALF_UP
getcontext().prec = 60

def partitions(speed, divisor, coefficient):
    # lo,hi,current speed,carry offset; None means carry was reset to zero.
    pieces = [(0, 65535, speed, 0)]
    for _ in range(5):
        result = []
        for lo,hi,v,offset in pieces:
            q = v // divisor
            if not q:
                result.append((lo,hi,v,None))
                continue
            assert offset is not None  # reset only occurs at a fixed point
            total = q * coefficient + offset
            first,last = (total+lo)//65536, (total+hi)//65536
            for loss in range(first,last+1):
                left = max(lo, loss*65536-total)
                right = min(hi, (loss+1)*65536-1-total)
                if left > right:
                    continue
                new = v-loss
                assert 0 <= new <= v <= 65535
                carry = total-loss*65536 if new >= divisor else None
                if carry is not None:
                    assert 0 <= left+carry <= right+carry <= 65535
                result.append((left,right,new,carry))
        assert result[0][0] == 0 and result[-1][1] == 65535
        assert all(a[1]+1 == b[0] for a,b in zip(result,result[1:]))
        pieces = result
    return pieces

def main():
    report = []
    for k in (256,192,128,64):
        gamma = Decimal(k)*(1-(1-Decimal(1)/k)**(Decimal(2)/5))
        c = int((gamma*65536).to_integral_value(rounding=ROUND_HALF_UP))
        errors,witnesses = {},{}
        for speed in range(65536):
            native = speed-speed//k
            native -= native//k
            for lo,hi,new,carry in partitions(speed,k,c):
                error = new-native
                errors[error] = errors.get(error,0)+hi-lo+1
                witnesses.setdefault(error, {'speed':speed,'initial_carry':lo})
                if speed < k:
                    assert new == speed and carry is None
                assert -2 <= error <= 2, (k,speed,lo,error)
        assert sum(errors.values()) == 65536**2
        report.append({'divisor':k,'exact_coefficient':str(gamma),
                       'q16_coefficient':c,'initial_states':65536**2,
                       'five_vs_two_error_histogram':dict(sorted(errors.items())),
                       'error_witnesses':witnesses})
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
