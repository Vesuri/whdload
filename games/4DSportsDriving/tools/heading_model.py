#!/usr/bin/env python3
"""Check the 50 Hz cardinal approach against native 20 Hz common-time endpoints."""
import json

def word(n):
    return (n + 32768) % 65536 - 32768

def native(heading):
    error = (heading + 128) % 256 - 128
    return word(heading + (-1 if error > 0 else 1)) if 0 < abs(error) < 8 else heading

def a4000(heading, carry):
    error = (heading + 128) % 256 - 128
    if not 0 < abs(error) < 8:
        return heading, 0
    numerator = carry + (-2 if error > 0 else 2)
    step = (abs(numerator) // 5) * (-1 if numerator < 0 else 1)
    carry = numerator - 5 * step
    heading = word(heading + step)
    return heading, carry if heading % 256 else 0

for start in range(-32768, 32768):
    heading, carry = start, 0
    for _ in range(5):
        heading, carry = a4000(heading, carry)
    assert heading == native(native(start)), (start, heading)
print(json.dumps({"full_word_cases": 65536, "common_time_seconds": 0.1,
                  "max_heading_error": 0}, indent=2))
