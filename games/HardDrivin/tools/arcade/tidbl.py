"""The MSP's software doubles (TI 34010 C runtime).

The layout looks like IEEE: sign, 11-bit exponent with bias 1023, 52-bit
mantissa. But there is no hidden bit: the mantissa holds 0.1xxx... with an
explicit leading one, so the value is 0.M * 2^(e-1023). Read as IEEE, every
value comes out as v + 2^floor(log2 v) (1.0 reads as 3.0, 32.2 as 96.2).
Checked in MAME against 4,690 logged operations (multiply, divide, add,
subtract, int conversions): all match except 11 add/subtract cancellations,
where the library keeps only about 32 mantissa bits.
"""
import math
import struct


def from_bits(b):
    e = (b >> 52) & 0x7ff
    if e == 0:
        return 0.0
    try:
        v = math.ldexp((b & ((1 << 52) - 1)) / float(1 << 52), e - 1023)
    except OverflowError:
        v = math.inf
    return -v if b >> 63 else v


def from_bytes_le(b8):
    return from_bits(struct.unpack('<Q', b8)[0])


def from_hex_be(h):
    return from_bits(int(h, 16))


def from_ieee(x):
    """The value of a double that was decoded as IEEE."""
    return from_bits(struct.unpack('<Q', struct.pack('<d', x))[0])
