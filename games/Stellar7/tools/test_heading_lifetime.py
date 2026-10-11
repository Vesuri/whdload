#!/usr/bin/env python3
"""Operand-address checks for heading lifetime evidence."""
import unittest
import capstone
from heading_lifetime import accesses


class Addressing(unittest.TestCase):
    def access(self, encoded, **values):
        decoder=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000)
        decoder.detail=True
        insn=next(decoder.disasm(bytes.fromhex(encoded),0x100))
        regs=[0]*17
        for name,value in values.items():
            regs[int(name[1:])+(8 if name[0]=='a' else 0)]=value
        return accesses(insn,regs)

    def test_direct_and_indirect_alias(self):
        self.assertEqual(self.access('302b005e',a3=0x1000),[(0x105e,2,True,False)])
        self.assertEqual(self.access('2010',a0=0x105e),[(0x105e,4,True,False)])

    def test_index_width_and_zero_displacement(self):
        self.assertEqual(self.access('2030005e',a0=0x1000,d0=0xfffe),[(0x105c,4,True,False)])
        self.assertEqual(self.access('20300800',a0=0x1000,d0=0xfffffffe),[(0xffe,4,True,False)])
        self.assertEqual(self.access('20300000',a0=0x1000,d0=2),[(0x1002,4,True,False)])

    def test_address_register_updates_are_ordered(self):
        self.assertEqual(self.access('20d8',a0=0x1000),[(0x1000,4,True,False),(0x1004,4,False,True)])
        self.assertEqual(self.access('2020',a0=0x1000),[(0xffc,4,True,False)])

    def test_movem_span(self):
        self.assertEqual(self.access('48e70330',a7=0x1000),[(0xff0,16,False,True)])
        self.assertEqual(self.access('4cdf0cc0',a7=0x1000),[(0x1000,16,True,False)])

    def test_absolute_sign_and_pc_index(self):
        self.assertEqual(self.access('3038fffe'),[(0xfffffffe,2,True,False)])
        self.assertEqual(self.access('203b085e',d0=4),[(0x164,4,True,False)])

    def test_address_only_does_not_read_heading(self):
        self.assertEqual(self.access('41eb005e',a3=0x1000),[])


if __name__=='__main__':unittest.main()
