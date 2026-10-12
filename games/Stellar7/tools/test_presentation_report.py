import json
from pathlib import Path
import tempfile
import unittest
from presentation_report import inspect


class BeamTiming(unittest.TestCase):
    def report(self, events):
        scratch=Path(__file__).resolve().parent.parent/'tmp'
        with tempfile.TemporaryDirectory(dir=scratch) as path:
            folder=Path(path)
            (folder/'presentation-events.json').write_text(json.dumps(dict(fields=2,field_hz=60,events=events)))
            return inspect(folder)

    def event(self, epoch, site, line, hp, lol):
        return dict(epoch=epoch,site=site,beam=0x80000000|(lol<<23)|(line<<8)|hp)

    def test_last_clock_and_previous_line_register(self):
        # First line is short. HP=0 is its final clock; HP=1 exposes
        # the previous VP but the next line's LOL. They are one clock apart.
        events=[self.event(0,'vbl',0,50,0),
                self.event(0,'polygon_wait_start',2,0,0),
                self.event(0,'polygon_wait_end',2,1,1),
                self.event(1,'vbl',0,50,1)]
        result=self.report(events)
        self.assertAlmostEqual(result['scopes']['polygon_wait']['total_ms'],1000/60/59832.5)
        self.assertEqual(result['geometry']['colour_clocks'],119665)

    def test_field_wrap_and_partial_calls(self):
        events=[self.event(0,'vbl',0,50,0),
                self.event(0,'waitblit_end',10,30,0),
                self.event(0,'waitblit_start',262,200,0),
                self.event(1,'vbl',0,50,1),
                self.event(1,'waitblit_end',0,100,1),
                self.event(1,'waitblit_start',1,40,0)]
        result=self.report(events)['scopes']['graphics_waitblit']
        self.assertEqual(result['calls'],1)
        self.assertAlmostEqual(result['mean_ms'],127*1000/60/59832.5)

    def test_beam_wrap_precedes_delayed_vbl_handler(self):
        result=self.report([self.event(0,'vbl',1,30,1),
                            self.event(0,'actors_start',262,200,0),
                            self.event(0,'actors_end',1,40,0),
                            self.event(1,'vbl',4,50,1)])
        self.assertEqual(result['scopes']['actors']['calls'],1)
        self.assertAlmostEqual(result['scopes']['actors']['mean_ms'],295*1000/60/59832.5)

    def test_bad_long_line_and_backwards_beam_rejected(self):
        for middle in ([self.event(0,'actors_start',3,10,0)],
                       [self.event(0,'actors_start',3,20,1),self.event(0,'actors_end',3,10,1)]):
            with self.assertRaises(AssertionError):
                self.report([self.event(0,'vbl',0,50,0),*middle,self.event(1,'vbl',0,50,1)])

    def test_nested_scope_rejected(self):
        with self.assertRaises(AssertionError):
            self.report([self.event(0,'vbl',0,50,0),self.event(0,'actors_start',3,10,1),self.event(0,'actors_start',3,20,1),self.event(1,'vbl',0,50,1)])


if __name__=='__main__':unittest.main()
