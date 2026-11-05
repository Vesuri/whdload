-- A1: take a snapshot every 5 emulated seconds.
local m = manager.machine
local nextsnap = 5
hd_sub = emu.add_machine_frame_notifier(function()
  if m.time:as_double() >= nextsnap then
    m.video:snapshot()
    print(string.format("snap t=%.2f frame=%d", m.time:as_double(), m.screens[":mainpcb:screen"]:frame_number()))
    nextsnap = nextsnap + 5
  end
end)
