# Granulator III Tap

This is a Tap-enabled copy of Ableton's Granulator III. The factory device is
left unchanged.

Keep these two files together:

- `Granulator III Tap.amxd`
- `tap_granulator_bridge.js`

The JavaScript is intentionally resolved as a sibling file. Do not add it to
the AMXD dependency cache with a relative `bootpath`; Max treats that as an
invalid directory inside the packed device.

Drag `Granulator III Tap.amxd` into Live in place of the factory Granulator III.
When this device is selected, Tap shows its sample waveform, the Position and
Scan Distance region, and the device's real-time grain playheads.

The device sends visualization data only to `127.0.0.1:22117`; no network data
leaves the Mac. Re-run `tools/build_granulator_tap.py` if you ever update Ableton's
factory Granulator III to rebuild the Tap enabled from the installed device.
