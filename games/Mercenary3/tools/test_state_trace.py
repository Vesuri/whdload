import copy
import unittest

from state_trace import START, END, compare, decode


class StateTraceTests(unittest.TestCase):
    def test_snapshot_exact_ranges_and_big_endian(self):
        data = bytearray(END - START)
        data[0x7180 - START:0x7182 - START] = b'\x12\x34'
        data[0xb31d - START:0xb31f - START] = b'\xab\xcd'
        state = decode(data)
        self.assertEqual(state['frames'], 0x1234)
        self.assertEqual(len(state['pose']), 64)
        self.assertEqual(len(state['clock']), 8)
        self.assertTrue(state['objects_af36'].endswith('ab'))
        self.assertTrue(state['objects_b31e'].startswith('cd'))
        changed = bytearray(data)
        changed[-1] = 1
        self.assertNotEqual(state['image_sha256'], decode(changed)['image_sha256'])
        with self.assertRaises(RuntimeError):
            decode(data[:-1])

    def test_first_difference_and_length(self):
        a = {'records': [{'pose': 'aa'}, {'pose': 'bb', 'frames': 1}]}
        self.assertIsNone(compare(a, copy.deepcopy(a)))
        b = copy.deepcopy(a)
        b['records'][1].update(pose='cc', frames=2)
        self.assertEqual(compare(a, b), 'first differing pass 1: frames, pose')
        b['records'].pop()
        self.assertIn('pass 1: missing record', compare(a, b))
        b['route'] = [[10, []]]
        self.assertEqual(compare(a, b), 'incompatible trace definition: route')
        with self.assertRaises(ValueError):
            compare({'records': []}, {'records': []})


if __name__ == '__main__':
    unittest.main()
