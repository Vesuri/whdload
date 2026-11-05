-- Float value trace for plan step D (see ARCADE_ROMS.md, "MSP vehicle model").
-- dofile() this from a plan; it returns { on = function(bool), dump = function(tag) }.
-- dump writes MSP RAM $74DE80..$760000 (the model's globals) as little-endian
-- words to HD_RUN/ram_TAG.bin, for tools/mspram.py, and the program area
-- $700000..$74DE80 to code_TAG.bin.
-- Read taps on the MSP software float entries fire on the instruction fetch
-- after the CALLR, when SP holds the return address and the operands are on
-- the A14 stack (a double is 0x40 bits, little-endian; the second operand is on
-- top). Output (HD_RUN/ftrace.txt), one line per call:
--   F ENTRY RET A8 A B       operands as hex doubles (- when the entry has none)
--   = RESULT | = i A8        the result, from the routine's RETS
--   S frame                  the MSP frame step $7002B0 starts
--   R                        the 68010 finished copying a result block
local m = manager.machine
local cpu = m.devices[":mainpcb:msp"]
local msp = cpu.spaces["program"]
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local out = io.open(os.getenv("HD_RUN") .. "/ftrace.txt", "w")
local on = false
local frame = 0

-- entry -> number of double operands on the A14 stack
local ENTRIES = {
  [0x74b400] = 2, [0x74b600] = 2, [0x74ba00] = 2, [0x74c0a0] = 2, [0x74c000] = 2,
  [0x74c400] = 2, [0x74de00] = 1, [0x74d260] = 0, [0x74ce00] = 1,
  [0x74d600] = 2, [0x74d620] = 2, [0x74d640] = 2, [0x74d660] = 2, [0x74dc00] = 2,
}

local function dhex(a)
  return string.format("%04x%04x%04x%04x", msp:read_u16(a + 48), msp:read_u16(a + 32), msp:read_u16(a + 16), msp:read_u16(a))
end

local reg = cpu.state
ft_taps = {}
for e, n in pairs(ENTRIES) do
  ft_taps[#ft_taps + 1] = msp:install_read_tap(e, e + 15, "ft" .. e, function(offset, data, mask)
    if not on or offset ~= e then return end
    local a14, sp = reg["A14"].value, reg["SP"].value
    local ret = msp:read_u32(sp)
    local a = n >= 2 and dhex(a14 - 0x80) or "-"
    local b = n >= 1 and dhex(a14 - 0x40) or "-"
    out:write(string.format("F %06x %06x %08x %s %s\n", e, ret & 0xffffff, reg["A8"].value & 0xffffffff, a, b))
  end)
end
-- results: the RETS of the double-returning exits (result on top of A14) and
-- of the double -> int exits (A8)
for _, e in ipairs({ 0x74bd40, 0x74beb0, 0x74c7a0, 0x74d3d0, 0x74d430 }) do
  ft_taps[#ft_taps + 1] = msp:install_read_tap(e, e + 15, "ftr" .. e, function(offset)
    if on and offset == e then out:write(string.format("= %s\n", dhex(reg["A14"].value - 0x40))) end
  end)
end
for _, e in ipairs({ 0x74cf60, 0x74d0a0, 0x74d0e0, 0x74d1b0 }) do
  ft_taps[#ft_taps + 1] = msp:install_read_tap(e, e + 15, "fti" .. e, function(offset)
    if on and offset == e then out:write(string.format("= i %08x\n", reg["A8"].value & 0xffffffff)) end
  end)
end
ft_taps[#ft_taps + 1] = msp:install_read_tap(0x7002b0, 0x7002bf, "ftframe", function(offset)
  if offset ~= 0x7002b0 then return end
  frame = frame + 1
  if on then out:write(string.format("S %d\n", frame)) end
end)
ft_taps[#ft_taps + 1] = main:install_write_tap(0xff8eca, 0xff8ecb, "ftres", function()
  if on then out:write("R\n") end
end)

local function dump(tag)
  local f = io.open(os.getenv("HD_RUN") .. "/ram_" .. tag .. ".bin", "wb")
  local w = {}
  for a = 0x74de80, 0x75fff0, 16 do w[#w + 1] = string.pack("<I2", msp:read_u16(a)) end
  f:write(table.concat(w)); f:close()
  -- the program and constants as the MSP sees them, to compare with msp/sec00
  f = io.open(os.getenv("HD_RUN") .. "/code_" .. tag .. ".bin", "wb")
  w = {}
  for a = 0x700000, 0x74de70, 16 do w[#w + 1] = string.pack("<I2", msp:read_u16(a)) end
  f:write(table.concat(w)); f:close()
  out:write(string.format("D %s %d\n", tag, frame))
end

return {
  on = function(v)
    on = v
    out:write(v and "ON\n" or "OFF\n")
    out:flush()
  end,
  dump = dump,
}
