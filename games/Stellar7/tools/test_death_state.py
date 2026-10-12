import unittest
from death_state import validate

class NaturalDeath(unittest.TestCase):
    def record(self, decline=False):
        return dict(stage=3, errors=0, injection_tick=300, exit_tick=1800,
            exit_energy=65464, exit_active=0, exit_death=1,
            exit_field=7200, dialog_start=7210, dialog_answer=7270,
            resume_last=7300, resume_field=7301, resume_credit=60, field_hz=60,
            resume_ticks=0, resume_renders=0, resume_phase=0, resume_energy=680,
            resume_level=0 if decline else 6, resume_death=0,
            armed_level=6, armed_session=7, resume_session=8, captured_session=8,
            dialogs=1, dialog_choice=2, menu_count=1, menu_running=0,
            menu_session=7, menu_tick=1800, menu_field=7280)

    def test_continue_and_no(self):
        for decline in (False, True):
            validate(self.record(decline), natural=True, decline=decline)

    def test_wrong_level_after_no(self):
        r=self.record(True); r['resume_level']=6
        with self.assertRaises(AssertionError): validate(r,natural=True,decline=True)

    def test_wrong_menu_session_or_answer(self):
        for field,value in [('menu_session',1),('dialog_choice',1),('menu_count',0)]:
            r=self.record(True); r[field]=value
            with self.assertRaises(AssertionError): validate(r,natural=True,decline=True)

    def test_no_natural_death_or_reset(self):
        for field,value in [('exit_tick',300),('resume_ticks',1),('captured_session',7)]:
            r=self.record(True); r[field]=value
            with self.assertRaises(AssertionError): validate(r,natural=True,decline=True)

if __name__=='__main__': unittest.main()
