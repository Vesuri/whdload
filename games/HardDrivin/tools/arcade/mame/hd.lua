-- Scripted harddriv session. HD_PLAN names a Lua file returning a table:
--   events = { {t=SECONDS, <actions>}, ... } in time order, where t is emulated
--   time since the script started. Actions:
--   coin/key/abort = 0|1; wheel (12-bit raw, centre 0x800); brake (12-bit amount
--   pressed: the strain gauge reads 0xfff released); gas/clutch/shiftx/shifty
--   (8-bit raw); snap = true; log = true|false; exit = true;
--   ramp = {NAME, TO, SECONDS} moves input NAME linearly to TO;
--   cruise = MPH|false holds the speed with the gas pedal (PI on $8DEA);
--   head = DEGREES|false steers to a heading (0 = start line direction, right
--   positive) with a PD controller on the heading and the yaw rate $8DE8;
--   call = FUNCTION is called (for example ftrace.lua's switch).
-- plan.road = true makes every surface road: the MSP's per-wheel surface type
-- writes (front $750FB0, rear $750FD0, from the polygon under the wheel) have
-- grass (1) replaced by road (0). That removes grass drag and grip and the
-- off-road countdown, which reads the same variables through the result block.
-- Input values are held and re-applied every frame. MAME's harddriv driver does
-- not save its own state, so loading a save state stalls the MSP: every session
-- boots from power-on with pristine nvram, which is deterministic.
--
-- Log (HD_RUN/log.txt):
--   T time                                   emulated time of script time 0
--   E time frame index                       event applied
--   C time words...                          calibration RAM when logging starts
--   R time frame tick inputs results adc srf one MSP result
-- inputs = MSP $794000, 0x21 words; results = MSP $790000, 0x86 words (both
-- read from MSP RAM when the 68010 finishes copying the result block);
-- adc = $FFFF8000..$FFFF8017 as words; tick = the 244 Hz counter $FFFF8014;
-- srf = the front and rear surface types the MSP computed, before plan.road.
local m = manager.machine
local plan = dofile(os.getenv("HD_PLAN"))
local ports = m.ioport.ports
local F = {
  coin = ports[":mainpcb:IN0"].fields["Coin 1"],
  key = ports[":mainpcb:a80000"].fields["Key"],
  abort = ports[":mainpcb:a80000"].fields["Abort"],
  wheel = ports[":mainpcb:12BADC.0"].fields["Steering Wheel"],
  brake = ports[":mainpcb:12BADC.1"].fields["Brake Pedal"],
  gas = ports[":mainpcb:8BADC.0"].fields["Gas Pedal"],
  clutch = ports[":mainpcb:8BADC.1"].fields["Clutch Pedal"],
  shifty = ports[":mainpcb:8BADC.3"].fields["Shifter Lever Y"],
  shiftx = ports[":mainpcb:8BADC.4"].fields["Shifter Lever X"],
}
local hold = { coin = 0, key = 0, abort = 0, brake = 0 }
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local msp = m.devices[":mainpcb:msp"].spaces["program"]
local screen = m.screens[":mainpcb:screen"]
local out = io.open(os.getenv("HD_RUN") .. "/log.txt", "w")
local logging = false
local t0 = m.time:as_double()
local idx = 1
out:write(string.format("T %.6f\n", t0))

local function words(space, addr, n, step)
  local w = {}
  for i = 0, n - 1 do w[#w + 1] = string.format("%04x", space:read_u16(addr + i * step)) end
  return table.concat(w)
end

-- The 68010 copies the MSP result block to $FF8DC0..$FF8ECB with ascending
-- word writes; the write of the last word marks a completed result.
local srf = { [0x750fb0] = 0, [0x750fd0] = 0 }
hd_srf = msp:install_write_tap(0x750fb0, 0x750fdf, "hd_surface", function(offset, data, mask)
  if srf[offset] == nil then return end
  srf[offset] = data
  if plan.road and data == 1 then return 0 end
end)

hd_tap = main:install_write_tap(0xff8eca, 0xff8ecb, "hd_result", function(offset, data, mask)
  if logging then
    out:write(string.format("R %.6f %d %04x%04x %s %s %s %02x%02x\n", m.time:as_double(), screen:frame_number(),
      main:read_u16(0xffff8014), main:read_u16(0xffff8016),
      words(msp, 0x794000, 0x21, 16), words(msp, 0x790000, 0x86, 16), words(main, 0xffff8000, 12, 2),
      srf[0x750fb0] & 0xff, srf[0x750fd0] & 0xff))
  end
end)

local ramps = {}
local cruise = nil   -- { mph, integral }
local head = nil

local function s16(v) return v >= 0x8000 and v - 0x10000 or v end

local function apply(ev)
  -- controllers first, so inputs set by the same event win over their reset
  if ev.cruise ~= nil then
    cruise = ev.cruise and { mph = ev.cruise, i = cruise and cruise.i or 0.3 } or nil
    if not cruise then hold.gas = 0 end
  end
  if ev.head ~= nil then
    head = ev.head or nil
    if not head then hold.wheel = 0x800 end
  end
  for k, v in pairs(ev) do
    if F[k] then hold[k] = v; ramps[k] = nil end
  end
  if ev.ramp then
    local k, to, dur = ev.ramp[1], ev.ramp[2], ev.ramp[3]
    ramps[k] = { from = hold[k] or 0, to = to, t0 = m.time:as_double(), dur = dur }
  end
  if ev.log ~= nil then
    logging = ev.log
    if logging then
      -- brake range $FF4400, brake baseline $FF904A, pedal min/max $FF9026..,
      -- wheel centre $FF916E and gain $FF9178
      out:write(string.format("C %.6f %s %s %s %s\n", m.time:as_double(), words(main, 0xff4400, 1, 2),
        words(main, 0xff904a, 2, 2), words(main, 0xff9026, 8, 2), words(main, 0xff916e, 6, 2)))
    end
  end
  if ev.call then ev.call() end
  if ev.snap then m.video:snapshot() end
  if ev.exit then out:close(); m:exit() end
end

hd_sub = emu.add_machine_frame_notifier(function()
  local t = m.time:as_double() - t0
  while idx <= #plan.events and plan.events[idx].t <= t do
    local ev = plan.events[idx]; idx = idx + 1
    out:write(string.format("E %.6f %d %d\n", m.time:as_double(), screen:frame_number(), idx - 1)); out:flush()
    apply(ev)
  end
  local now = m.time:as_double()
  for k, r in pairs(ramps) do
    local f = math.min(1, (now - r.t0) / r.dur)
    hold[k] = math.floor(r.from + (r.to - r.from) * f + 0.5)
    if f >= 1 then ramps[k] = nil end
  end
  if cruise then
    -- gas fraction = 0.08 * error (MPH) + integral; the integral moves at
    -- 0.05/s per MPH, and not while the pedal is saturated in that direction
    local err = cruise.mph - main:read_u16(0xff8dea) / 4.07
    local g = cruise.i + 0.08 * err
    if not ((g >= 1 and err > 0) or (g <= 0 and err < 0)) then
      cruise.i = math.max(0, math.min(1, cruise.i + 0.05 * err / 60))
    end
    g = math.max(0, math.min(1, cruise.i + 0.08 * err))
    hold.gas = math.floor(12.75 + 242.25 * g + 0.5)
  end
  if head then
    -- forward axis = matrix row 1, components (X, Z, Y) at $FF8DC6
    local fx, fz = s16(main:read_u16(0xff8dc6)), s16(main:read_u16(0xff8dc8))
    local err = (head - math.deg(math.atan(-fz, fx)) + 180) % 360 - 180
    local yaw = s16(main:read_u16(0xff8de8)) * 1.416
    local w = 0x800 + 16 * err - 4 * yaw
    hold.wheel = math.floor(math.max(0x010, math.min(0xff0, w)) + 0.5)
  end
  for k, v in pairs(hold) do F[k]:set_value(k == "brake" and 0xfff - v or v) end
end)
