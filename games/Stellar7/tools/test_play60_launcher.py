"""Verify what make play60 asks common/run.sh to run, without booting."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Launcher(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='play60-test-',dir=ROOT/'tmp')
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        # A stand-in common/: run.sh reports what it was asked to run.
        (self.work/'common').mkdir()
        p=self.work/'common/run.sh'
        p.write_text('#!/bin/sh\nprintf "variant=%s\\nargs=%s\\n" "$VARIANT" "$WHD_ARGS"\n');p.chmod(0o755)

    def launch(self,**extra):
        env=dict(HOME=os.environ['HOME'],PATH=os.environ['PATH'],COMMON=str(self.work/'common'),**extra)
        result=subprocess.run(['/bin/bash',str(ROOT/'tools/play60.sh')],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return dict(line.split('=',1) for line in result.stdout.splitlines())

    def test_release_slave_with_custom1(self):
        # The slave selects the simulation from the CPU (tools/play60_smoke.py boots it).
        for setup in ('','a500-1.5m','a1200-fast','a1200-060'):
            with self.subTest(setup=setup):
                self.assertEqual(self.launch(SETUP=setup,VARIANT='Stellar7-Sim60'),dict(variant='Stellar7',args='CUSTOM1=1'))

    def test_explicit_whdload_arguments(self):
        self.assertEqual(self.launch(WHD_ARGS='CUSTOM1=1 CUSTOM3=1')['args'],'CUSTOM1=1 CUSTOM3=1')

if __name__=='__main__':unittest.main()
