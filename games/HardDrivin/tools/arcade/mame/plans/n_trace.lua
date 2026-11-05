-- Axle loads for H3 round 11: runs plans/HD_INNER.lua and, at the start of each
-- MSP frame step ($7002B0), writes the emulated time and the z components of
-- the front and rear wheel force vectors ($74E3C0 and $74E480, +80; z down, so
-- -N) as hex doubles to HD_RUN/loads.txt. Decode with tidbl.from_hex_be.
local m = manager.machine
local msp = m.devices[":mainpcb:msp"].spaces["program"]
local out = io.open(os.getenv("HD_RUN") .. "/loads.txt", "w")
local function dhex(a)
  return string.format("%04x%04x%04x%04x", msp:read_u16(a + 48), msp:read_u16(a + 32), msp:read_u16(a + 16), msp:read_u16(a))
end
n_trace_tap = msp:install_read_tap(0x7002b0, 0x7002bf, "nframe", function(offset)
  if offset ~= 0x7002b0 then return end
  out:write(string.format("%.6f %s %s\n", m.time:as_double(), dhex(0x74e3c0 + 0x80), dhex(0x74e480 + 0x80)))
end)
return dofile(os.getenv("HD_TOOLS") .. "/plans/" .. os.getenv("HD_INNER") .. ".lua")
