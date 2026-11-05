import unittest
from contact_effect_state import validate_rows

class ContactEffect(unittest.TestCase):
    def rows(self,kind='shield'):
        return [dict(before=dict(pc=0x35a8 if kind=='shield' else 0x38b2,tick=502,type=10,health=1,damage=5 if kind=='shield' else 10,energy=616,shield=481,mine_type=43,**{'class':255}),after=dict(pc=0x35ae if kind=='shield' else 0x38b8,tick=502,health=0,energy=616))]
    def test_native_contacts(self):
        for kind in ('shield','mine'):validate_rows(kind,self.rows(kind))
    def test_wrong_boundary(self):
        for field,value in [('pc',0x35b0),('tick',503),('energy',612)]:
            r=self.rows();r[0]['after'][field]=value
            with self.assertRaises(AssertionError):validate_rows('shield',r)
    def test_no_lethal_contact(self):
        for r in ([],self.rows()):
            if r:r[0]['after']['health']=1
            with self.assertRaises(AssertionError):validate_rows('shield',r)
    def test_wrong_effect(self):
        for kind,field,value in [('shield','shield',0),('mine','mine_type',42),('mine','damage',5),('shield','class',254)]:
            r=self.rows(kind);r[0]['before'][field]=value
            with self.assertRaises(AssertionError):validate_rows(kind,r)

if __name__=='__main__':unittest.main()
