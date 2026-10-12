import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import presentation_buffers as pb


class ScanoutStability(unittest.TestCase):
    def report(self, second_buffer=0, changed=False, strict=True):
        data=bytearray(0x823c)
        origins=[]
        for buffer in range(3):
            at=0x71da+40*buffer
            struct.pack_into('>2H',data,at,40,200)
            data[at+5]=5 if buffer==2 else 4
            pointers=[0x10000+buffer*0x10000+plane*8000 for plane in range(5)]
            struct.pack_into('>8I',data,at+8,*pointers,0,0,0)
            origins.append(pointers)
        fields=[]
        for index,buffer in enumerate((0,second_buffer)):
            dma=bytearray(58*16000)
            for plane in range(4):
                for word in range(4000):
                    at=58*(plane*4000+word)
                    value=int(changed and index==1 and plane==0 and word==7)
                    struct.pack_into('<HQHI',dma,at,0x110+2*plane,value,2,origins[buffer][plane]+2*word)
                    struct.pack_into('<h',dma,at+29,6)
            fields.append(SimpleNamespace(index=index,dma_size=58,dma=dma))
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent/'tmp') as name:
            folder=Path(name);(folder/'state.bin').write_bytes(data)
            with patch.object(pb.barto,'load',return_value=SimpleNamespace(fields=fields)):
                return pb.inspect(folder,strict)

    def test_unchanged_displayed_buffer(self):
        self.assertEqual(self.report()['same_buffer_word_changes'],[])

    def test_changed_displayed_word_rejected(self):
        report=self.report(changed=True,strict=False)
        self.assertEqual(report['same_buffer_word_changes'],[dict(field=1,buffer=0,changed_words=1)])
        with self.assertRaisesRegex(AssertionError,'displayed bitmap content changes'):
            self.report(changed=True)

    def test_new_buffer_can_have_new_pixels(self):
        self.assertEqual(self.report(second_buffer=1,changed=True)['same_buffer_word_changes'],[])


if __name__=='__main__':unittest.main()
