#!/usr/bin/env python3
"""Audit the native car+$42 lifetime; no emulator or game mutation.

This is a control-flow proof for the supplied executable, not a handling test.
The no-skid branch cannot consume the damped angle as speed loss. All grounded
returns clear the angle; airborne entry preserves it without running decay.
"""
from pathlib import Path
import hashlib, json, re, struct
import capstone
root = Path(__file__).resolve().parents[1]
raw = (root / "tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts").read_bytes()
code = raw[0x28:0x28+0x3a04c]
md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
items = list(md.disasm(code[0xf7d6:0xfe32], 0xf7d6))
assert sum(i.size for i in items) == 0xfe32-0xf7d6
ins = {i.address:i for i in items}
def exact(address, hexbytes):
    expected = bytes.fromhex(hexbytes)
    assert code[address:address+len(expected)] == expected, hex(address)
exact(0xfa46, "206d0008422800c7")  # clear the consumer's gate
exact(0xfd4c, "206d00084a2800c7670000d0") # zero gate goes to FE26
exact(0xfe26, "206d0008426800426000f9c4") # clear then sole epilogue
exact(0xf7da, "206d00084a2800c16614") # airborne skips whole grounded path
exact(0xf7f4, "4e5d4e75")
# Every call reachable below FA46 is a read-only arithmetic helper. Pin their
# complete implementations as well as the data-hunk vectors, not just names.
helpers = {
    -0x792c:(0x38a1e,"302f00046a0244404e75"),
    -0x7ba8:(0x3052c,"c1c14840e5984e75"),
    -0x7ba2:(0x30534,"302f0004064001006004302f0004024003ff41ecc8960c4001006320044002006404444060160c4001006306044002004440d0403030000044404e75d040303000004e75"),
}
for displacement,(address,expected) in helpers.items():
    assert struct.unpack_from(">I",raw,0x3a1dc+0x7ffe+displacement+2)[0] == address
    exact(address,expected)
for i in items:
    if i.address >= 0xfa46 and i.mnemonic == "jsr":
        assert i.op_str in {f"-${-d:x}(a4)" for d in helpers}, (hex(i.address),i.op_str)
# Four entries of the sole computed branch all resolve to FB98. They are data,
# even though a linear decoder labels them dc.w.
assert [0xfbce+struct.unpack_from(">h",code,0xfbb4+2*n)[0] for n in range(4)] == [0xfb98]*4
conditional = {"bne","beq","bge","bgt","ble","blt","bhi","bls","bcc","bcs","bvc","bvs","bpl","bmi"}
def successors(address, no_skid=False):
    i=ins[address]; op=i.mnemonic.split(".")[0]
    if address==0xfd54 and no_skid: return [0xfe26]
    if op=="rts": return []
    if op=="jmp":
        assert address==0xfbcc
        return [0xfb98]
    if op=="bra" or op in conditional:
        target=int(i.op_str[1:],16)
        return [target] if op=="bra" else [target,address+i.size]
    assert op!="dc", hex(address)
    return [address+i.size]
def walk(start,no_skid=False):
    seen=set(); pending=[(start,False)]
    while pending:
        address,cleared=pending.pop()
        if (address,cleared) in seen: continue
        seen.add((address,cleared))
        if address==0xfe2a: cleared=True
        if ins[address].mnemonic=="rts": assert cleared, "grounded return missed clear"
        pending.extend((n,cleared) for n in successors(address,no_skid))
    return {a for a,_ in seen}
grounded=walk(0xf7f8)
no_skid=walk(0xfa46,True)
assert 0xfd5c not in no_skid # sole downstream speed-loss angle read
assert 0xfa58 in no_skid and 0xfe2a in no_skid
# From the no-skid entry no instruction sets C7 again. Pointer-offset uses are
# enumerated, including ADDA aliases; arithmetic callees cannot touch car RAM.
assert [(i.address,i.op_str) for i in items if i.address in no_skid and "$c7" in i.op_str] == [(0xfa4a,"$c7(a0)"),(0xfd50,"$c7(a0)")]
# After the decay/canonicalization block, the only angle references are the
# gated read and unconditional clear; no address-of-$42 alias escapes.
assert [i.address for i in items if i.address>=0xfab6 and "$42" in i.op_str] == [0xfd5c,0xfe2a]
# Decay's scratch D0 cannot propagate: both branches overwrite it before use.
exact(0xfae0,"206d00084a68001c670000e6")
exact(0xfaec,"206d00083f28001c4eac86d4")
exact(0xfbd0,"302dfff4")
result={"native_routine_sha256":hashlib.sha256(code[0xf7d6:0xfe32]).hexdigest(),
        "grounded_reachable_instructions":len(grounded),
        "no_skid_reachable_instructions":len(no_skid),
        "pure_helpers_verified":len(helpers),
        "grounded_returns_clear_angle":True,
        "decayed_angle_reaches_speed_loss":False,
        "classification":"transient skid-demand angle; FA58 decay needs no rate conversion",
        "scope":"native control flow; not a natural handling or contact acceptance test"}
print(json.dumps(result,indent=2))
