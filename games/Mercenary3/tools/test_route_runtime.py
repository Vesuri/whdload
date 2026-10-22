"""Route boot policy and unsupported profiler guards, without an emulator."""
import os
import unittest
from unittest.mock import patch

from route_runtime import configure, require_instruction_backend


class RuntimeTests(unittest.TestCase):
    def test_030_retains_cpu_preset_and_uses_threaded_boot_io(self):
        with patch.dict(os.environ, {'AMIGA_SETUP': 'a1200-030', 'FSUAE_ARM': 'native'}, clear=True):
            configure()
            self.assertEqual(os.environ['AMIGA_SETUP'], 'a1200-030')
            self.assertEqual(os.environ['DETERMINISTIC'], '0')
            self.assertNotIn('CPU', os.environ)
            self.assertNotIn('EXTRA_ARGS', os.environ)

    def test_020_policy_and_explicit_override(self):
        with patch.dict(os.environ, {'FSUAE_ARM': 'native'}, clear=True):
            configure()
            self.assertEqual(os.environ['DETERMINISTIC'], '1')
        with patch.dict(os.environ, {'AMIGA_SETUP': 'a1200-030', 'DETERMINISTIC': '1',
                                     'FSUAE_ARM': 'native'}, clear=True):
            configure()
            self.assertEqual(os.environ['DETERMINISTIC'], '1')

    def test_rejects_hidden_boot_mode_override(self):
        for env in ({'EXTRA_ARGS': '--deterministic=1'}, {'RECORD': 'recording'}):
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
                configure()

    def test_unsupported_trace_backend_cannot_emit_costs(self):
        require_instruction_backend({'cpu_model': '68020'})
        for cpu in ('68030', '68040', '68060', ''):
            with self.assertRaisesRegex(RuntimeError, 'MODE=counter'):
                require_instruction_backend({'cpu_model': cpu})
