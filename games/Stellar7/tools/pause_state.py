#!/usr/bin/env python3
"""Verify that a known modal pause excludes paused fields but retains owed ticks."""
import argparse
import json
from sim60_state import read


def check(before, after, paused_fields):
    a, b = read(before), read(after)
    assert a['session'] == b['session'] and a['field_hz'] == b['field_hz']
    assert b['ticks'] == a['ticks']+1
    assert b['modal_resumes'] == a['modal_resumes']+1
    assert a['modal_depth'] == b['modal_depth'] == 0
    elapsed = b['observed_field']-a['observed_field']
    assert elapsed >= paused_fields
    assert b['clock_origin']-a['clock_origin'] == paused_fields*60
    credit_a = a['credit']+a['unaccounted_fields']*60
    credit_b = b['credit']+b['unaccounted_fields']*60
    assert credit_b == credit_a+(elapsed-paused_fields)*60-a['field_hz']
    return dict(paused_fields=paused_fields, active_fields=elapsed-paused_fields,
                pending_before=a['pending_ticks'], pending_after=b['pending_ticks'],
                debt_preserved=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('--paused-fields', type=int, required=True,
                        help='independently known excluded interval, 60 for the retained PAUSE_TEST runs')
    args = parser.parse_args()
    assert args.paused_fields >= 0
    print(json.dumps(check(args.before, args.after, args.paused_fields), sort_keys=True))
