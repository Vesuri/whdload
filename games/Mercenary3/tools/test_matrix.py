"""Matrix acceptance must reject mislabeled machines while retaining the advisory speed sanity."""
import unittest

from matrix import cells, frequency_sanity, render, validate


class MatrixTests(unittest.TestCase):
    def result(self, cell):
        return dict(machine=dict(cell['expected']), setup=cell['setup'],
                    extra_args=cell['extra'], slave_sha256='build', whd_args=cell['whd'],
                    per_frame=False, fields=500, deterministic=cell['deterministic'],
                    route=[[175, []], [185, ['JOY2_UP']], [140, ['JOY2_RIGHT']]])

    def test_uae_omitted_mmu_is_zero_but_not_an_030_mmu(self):
        for cell in (cells()[0], cells()[3]):
            result = self.result(cell)
            del result['machine']['mmu_model']
            if cell['expected']['mmu_model'] == '0':
                validate(result, cell, 'build', cell['whd'])
            else:
                with self.assertRaisesRegex(ValueError, 'mmu_model'):
                    validate(result, cell, 'build', cell['whd'])

    def test_rejects_wrong_frequency_or_non_exact_preset(self):
        cell = cells()[5]
        for key, wrong in [('cpu_frequency', '8000000'), ('cpu_cycle_exact', 'false'),
                           ('fastmem_size', '0')]:
            result = self.result(cell)
            result['machine'][key] = wrong
            with self.assertRaisesRegex(ValueError, key):
                validate(result, cell, 'build', '')

    def test_rejects_wrong_build_options_and_route(self):
        cell = cells()[4]
        for key, wrong in [('slave_sha256', 'other'), ('whd_args', ''),
                           ('fields', 504), ('per_frame', True)]:
            result = self.result(cell)
            result[key] = wrong
            with self.assertRaises(ValueError):
                validate(result, cell, 'build', 'MMU')

    def test_frequency_sanity_must_be_strict_and_have_both_results(self):
        rows = [dict(name='040-8-sanity', status='ok', result=dict(frames=118)),
                dict(name='040-25', status='ok', result=dict(frames=118))]
        self.assertFalse(frequency_sanity(rows)[0])
        rows[0]['result']['frames'] = 70
        self.assertTrue(frequency_sanity(rows)[0])
        rows[0]['status'] = 'FAILED'
        self.assertFalse(frequency_sanity(rows)[0])

    def test_failed_cells_are_not_reported_as_zero_fps(self):
        table = render([dict(name='failed', setup='a1200', options='', extra='',
                             status='FAILED: timeout')], 'unavailable')
        self.assertIn('| — | — | FAILED: timeout |', table)
        self.assertNotIn('0.00', table)
