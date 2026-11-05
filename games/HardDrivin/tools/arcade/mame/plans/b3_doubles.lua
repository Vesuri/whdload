-- B3 experiment, see ARCADE_ROMS.md (Time step and units).
-- B3 experiment: log MSP doubles (dt, position, velocity) with each result.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local msp = m.devices[":mainpcb:msp"].spaces["program"]
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local out = io.open(os.getenv("HD_RUN") .. "/doubles.txt", "w")
-- MSP doubles have no hidden bit: 0.M * 2^(e-1023) (tools/tidbl.py)
local function dbl(a)
  local b = msp:read_u16(a) | (msp:read_u16(a + 16) << 16) | (msp:read_u16(a + 32) << 32) | (msp:read_u16(a + 48) << 48)
  local e = (b >> 52) & 0x7ff
  if e == 0 then return 0 end
  local v = (b & ((1 << 52) - 1)) / (1 << 52) * 2.0 ^ (e - 1023)
  return b < 0 and -v or v
end
local function s32(a) local v = msp:read_u16(a) | (msp:read_u16(a + 16) << 16); if v >= 0x80000000 then v = v - 0x100000000 end; return v end
local function s16(a) local v = msp:read_u16(a); if v >= 0x8000 then v = v - 0x10000 end; return v end
b3_x = main:install_write_tap(0xff8eca, 0xff8ecb, "b3x", function(o, d, mk)
  if m.time:as_double() < 24.5 then return end
  out:write(string.format("%.6f ticks=%d dt=%.9g p=%.9g,%.9g,%.9g v=%.9g,%.9g,%.9g P=%d,%d,%d V=%d,%d,%d\n", m.time:as_double(),
    msp:read_u16(0x7940a0), dbl(0x751280), dbl(0x74ea20), dbl(0x74ea60), dbl(0x74eaa0), dbl(0x74e960), dbl(0x74e9a0), dbl(0x74e9e0),
    s32(0x790090), s32(0x7900b0), s32(0x7900d0), s16(0x7900f0), s16(0x790100), s16(0x790110)))
end)
return S.plan({ {t=25, gas=255}, {t=31, wheel=0x900}, {t=33, exit=true} })
