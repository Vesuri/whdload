-- Arcade clocks against emulated time: every frame from the start line, write
-- HD_RUN/clock.txt rows "time tick left lap lap_on running slow state":
-- tick $FFFF8014 (244.14 Hz), time left $FF9822 and lap time $FF9772 (both
-- in 1/250 s as displayed), lap clock running $FF976C, race clock running
-- $FF9816, crash-replay slow countdown $FF9818, race state $FF9802.
-- The car cruises at 40 MPH straight ahead on road surface for 60 s.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]

local function start()
  local out = io.open(os.getenv("HD_RUN") .. "/clock.txt", "w")
  clock_sub = emu.add_machine_frame_notifier(function()
    out:write(string.format("%.6f %d %d %d %d %d %d %d\n", m.time:as_double(), main:read_u32(0xffff8014),
      main:read_i32(0xff9822), main:read_i32(0xff9772), main:read_u16(0xff976c), main:read_u16(0xff9816),
      main:read_u16(0xff9818), main:read_u16(0xff9802)))
    out:flush()
  end)
end

local p = S.plan({ {t=22, call=start}, {t=24.5, cruise=40, head=0}, {t=85, exit=true} })
p.road = true
return p
