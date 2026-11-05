"""Verify slave selection against the shared machine presets without booting."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMMON=Path(os.environ.get('FSUAE_COMMON',Path.home()/'.local/share/amiga/fsuae_common.sh'))

class Launcher(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='play60-test-',dir=ROOT/'tmp')
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        # A stand-in common/: env.sh does nothing, run.sh reports what it was asked to run.
        (self.work/'common').mkdir()
        (self.work/'common/env.sh').write_text(':\n')
        p=self.work/'common/run.sh'
        p.write_text('#!/bin/sh\nprintf "variant=%s\\nargs=%s\\n" "$VARIANT" "$WHD_ARGS"\n');p.chmod(0o755)

    def launch(self,setup='',cpu=''):
        env=dict(HOME=os.environ['HOME'],PATH=os.environ['PATH'],FSUAE_COMMON=str(COMMON),COMMON=str(self.work/'common'),AMIGA_SETUP=setup)
        if cpu:env['CPU']=cpu
        return subprocess.run(['/bin/bash',str(ROOT/'tools/play60.sh')],env=env,capture_output=True,text=True)

    def test_explicit_and_default_cpu(self):
        for cpu,target in [('', 'sim68000'),('68000','sim68000'),('68010','sim68000'),('68020','sim60'),('68EC020','sim60'),('68060-NOMMU','sim60')]:
            with self.subTest(cpu=cpu):self.check(self.launch(cpu=cpu),target)

    def check(self,result,target):
        self.assertEqual(result.returncode,0,result.stderr)
        values=dict(line.split('=',1) for line in result.stdout.splitlines())
        self.assertEqual(values['variant'],'Stellar7-Sim68000' if target=='sim68000' else 'Stellar7-Sim60')
        self.assertEqual(values['args'],'CUSTOM1=1')

    def test_named_presets_override_cpu_before_build(self):
        for preset in ('a500','a500+','a1200','a1200-fast','a1200-030','a1200-040','a1200-060'):
            with self.subTest(preset=preset):
                slow=preset.startswith('a500')
                self.check(self.launch(preset,'68060' if slow else '68000'),'sim68000' if slow else 'sim60')

    def test_unknown_preset_stops_before_build(self):
        result=self.launch('invalid')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('variant=',result.stdout)

if __name__=='__main__':unittest.main()
