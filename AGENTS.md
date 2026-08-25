# Project instructions

## MIDI Remote Script and app protocol

- The paired iOS app repository lives at `/Users/simxn/Documents/Xcode/ProjectMIDI`.
- Do not add backward-compatibility parsing, migrations, legacy payload branches, or fallbacks unless the user explicitly requests them. The app and Remote Script ship as one matched pair.
- Any breaking wire-format or protocol-semantic change must bump both `secret_version_number` in `Tap.py` and `MIDIModule.secretScriptVersion` in the app to the same value. This exact handshake is the compatibility boundary.
- Keep shared algorithms and field ordering visibly mirrored between Python and Swift, and update tests in both repositories in the same change.
- Prefer one strict current format that rejects malformed or mismatched data over permissive recovery.
