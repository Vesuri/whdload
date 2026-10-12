# Kalms converters

Unmodified public-domain routines from Mikael Kalms' collection:
<https://github.com/Kalmalyzer/kalms-c2p>, commit
`d8ecf79a3325615305dd800ae7704b518e0d9dda`.

Upstream `readme.txt` declares all files outside `others/` public domain.
The 040 routine explicitly supports both 68040 and 68060.

| File | SHA-256 |
|---|---|
| c2p1x1_8_c5_030.s | 31bf210db133f206a262f54443d5470c6454be5dcc80806064fe04a1c89e4bf5 |
| c2p1x1_8_c5_040.s | 9fb2c00184c0a69edb41b9d234648ea8f0f1d478b02c745e6f377d36984df716 |

`tools/render_source.py` specialises the unchanged conversion bodies for the
three known 320-wide surfaces. It replaces initialised geometry variables with
constants, removes unused init/SMC routines and section/export directives, and
uses PC-relative reads. There is no runtime self-modification or code copying.
Generated assembly and binaries belong in `tmp/`.
