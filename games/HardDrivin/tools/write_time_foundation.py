from pathlib import Path
p=Path('src/HardDrivinHD.s')
s=p.read_text(encoding='latin1')
s=s.replace('\tIFD VERIFY_SLOW\n\tbsr\t_verify_slow_install\n\tENDC','\tIFD VERIFY_SLOW\n\tbsr\t_verify_slow_install\n\tENDC\n\tIFD VERIFY_TIME\n\tbsr _time_install\n\tENDC',1)
s=s.replace('_ct_ct2:\tdc.l\t0','_ct_ct2:\tdc.l\t0\n\tIFD VERIFY_TIME\n\tdc.l WHDLTAG_CUSTOM1_GET\n_ct_ct1:\tdc.l 0\n\tENDC',1)
s=s.replace('\tIFD VERIFY_SLOW\n\tINCLUDE "HardDrivinSlowVerify.s"\n\tENDC','\tIFD VERIFY_SLOW\n\tINCLUDE "HardDrivinSlowVerify.s"\n\tENDC\n\n\tIFD VERIFY_TIME\n\tINCLUDE "HardDrivinTime.s"\n\tENDC',1)
p.write_text(s,encoding='latin1')
