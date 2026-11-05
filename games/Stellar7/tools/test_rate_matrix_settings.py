"""Reject contradictory runtime settings without trusting the shared startup log."""
from pathlib import Path
import tempfile
import unittest
from rate_matrix_report import settings


class RuntimeSettings(unittest.TestCase):
    def check(self, ntsc=1, override=None, effective=None):
        meta=dict(cpu='68060-NOMMU',chip_kb=2048,fast_kb=4096,slow_kb=0,
                  ntsc_mode=ntsc,observed_exec_hz=60 if ntsc else 50,
                  extra_args='--uae_cpu_frequency=50000000 --uae_cpu_cycle_exact=true')
        options=dict(cpu_model='68060',cpu_speed='real',chipmem_size='4',fastmem_size='4',
                     bogomem_size='0',mmu_model='0',cpu_frequency='50000000',
                     cpu_cycle_exact='true')
        if ntsc:options['ntsc']='true'
        options.update(override or {})
        scratch=Path(__file__).resolve().parent.parent/'tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as path:
            folder=Path(path)
            # Intentionally contradictory copied frontend header.
            text='cpu = 68000\nntsc_mode = 0\n'+''.join(f'[UAE] [000] Set option {k} = "{v}"\n' for k,v in options.items())
            (folder/'emulator-settings.log').write_text(text)
            if effective is not None:
                values=dict(options,ntsc='true' if ntsc else 'false');values.pop('mmu_model')
                values.update(effective)
                (folder/'emulator-effective.uae').write_text(''.join(f'{k}={v}\n' for k,v in values.items()))
            return settings(folder,meta)

    def test_private_runtime_overrides_copied_header(self):
        self.assertEqual(self.check(effective={})['ntsc'],'true')

    def test_pal_default_and_omitted_disabled_mmu(self):
        self.assertEqual(self.check(ntsc=0,effective={})['ntsc'],'false')

    def test_conflicting_runtime_clock_or_cpu_rejected(self):
        for override in ({'ntsc':'false'},{'cpu_model':'68040'},{'cpu_frequency':'8000000'}):
            with self.subTest(override=override),self.assertRaises(AssertionError):
                self.check(override=override)

    def test_conflicting_effective_configuration_rejected(self):
        with self.assertRaises(AssertionError):self.check(effective={'cpu_model':'68040'})


if __name__=='__main__':unittest.main()
