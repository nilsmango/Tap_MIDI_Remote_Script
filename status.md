# Create Macro Hack Status

## Current State

The current approach works through rack replacement/hotswapping, not direct mutation of the loaded rack.

Main limitation:

- Ableton Live does not expose writable setters for macro mappings on already-loaded `RackDevice` objects.
- The mapping data is visible after creation.
- `.adg` files can be patched externally.
- The in-memory rack cannot currently be modified directly through the Remote Script API.

Because of this, the only workable route is:

1. Get an `.adg` representation of the current rack.
2. Patch the `.adg` XML by inserting:
   - `KeyMidi Channel=16`
   - `NoteOrController=<macroIndex>`
3. Hotswap/load the patched `.adg` back over the selected rack.

## Explored Approaches

### 1. Manual Save + Patch + Replace (Most Practical)

Workflow:

- User manually saves the selected rack as a preset.
- Tap patches the saved `.adg`.
- Tap hotswaps the patched preset back onto the selected rack.

This is currently the safest and most realistic route for Tap.

Potential workflow/button:

`Patch Saved Rack And Replace Selected`

Implementation idea:

- Expect a known preset name/location.
- Patch the `.adg`.
- Use:

```python
application().view.toggle_browse()
browser.load_item(...)
```

to hotswap the patched preset over the selected rack.

### 2. Automated UI Save via macOS Automation

Workflow:

- Tap triggers Live UI actions through macOS automation.
- Live saves the selected rack preset automatically.
- Tap patches the result.
- Tap hotswaps it back.

This is more automatic, but fragile and UI-dependent.

### 3. Patch `.als` Set File Directly

Workflow:

- Modify the gzipped XML inside the `.als` project file.
- Reload the Live Set.

This is technically powerful because `.als` is also patchable XML.

Limitation:

- Cannot update the currently running rack without reloading the Live Set.

## Additional Notes

- The test patcher bug causing Macro 1 to default to `-12` was fixed.
- `MacroControls.0 Manual Value` is now set to `0.5`.
- Macro 1 should now initialize at the middle position instead of minimum.
- The fix was copied into the installed Remote Script.
- `py_compile` passes successfully.

## Important Remaining Requirement

When only a single macro is created, the macro should inherit the correct default value from the mapped parameter controls automatically, instead of using a generic midpoint/default fallback.