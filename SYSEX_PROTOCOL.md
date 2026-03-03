# 7III Tap MIDI Remote Script - SysEx Protocol Documentation

## Parameter Metadata Enhancement (Manufacturer ID 0x7D)

### Overview
This document describes the enhanced parameter metadata sent by the MIDI remote script for device encoders. The metadata provides detailed information about each parameter to enable display of parameter values with units in the iOS app.

### Important Note on Units
The `value_string` field contains the formatted value at the parameter's current position. **Many parameters have empty `value_string`** - this is expected behavior since not all device parameters provide unit information.

To extract the unit, split `value_string` on space and take the last part:
- "1000.0 Hz" → unit = "Hz"
- "-2.5 dB" → unit = "dB"
- "25%" → unit = "%"
- "" (empty) → unit = nil (display just calculated value)

Your iOS app should gracefully handle missing units by displaying just the calculated numeric value.

### Actual vs Normalized Values

Ableton's `min` and `max` properties often return **normalized values** (0.0-1.0), not the actual display range you see in Live. The script tries multiple methods to get the **actual display values**:

#### Method 1: Display Properties (if available)
- `display_min` / `display_max`
- `min_display_value` / `max_display_value`

These return the actual values shown in Live's UI.

#### Method 2: Boundary String Parsing (fallback)
If display properties aren't available, the script calls `str_for_value(0.0)` and `str_for_value(1.0)` to get boundary strings, then extracts the numeric values:

**Example**:
- `str_for_value(0.0)` returns "0.0 %"
- `str_for_value(1.0)` returns "125.0 %"
- Extracted: min=0.0, max=125.0

This provides the actual display range (0-125%) instead of the normalized range (0.0-1.0).

**Note**: Some parameters may still return normalized values if the boundary strings can't be parsed. Your iOS app should handle both normalized and actual display values.

### Message Format

**Manufacturer ID**: `0x7D`

**Single Compact Message Format**:
```
name|min|max|default|value_items,name2|min2|max2|default2|value_items2,...

Parameters separated by comma (,)
Fields within each parameter separated by pipe (|)
Value items within a parameter separated by semicolon (;)
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Parameter name with automation/enabled prefixes |
| `min` | string | Minimum value with unit (e.g., "0.10 ms", "0.0 %") - used to know both range and unit |
| `max` | string | Maximum value with unit (e.g., "20.00 ms", "125.0 %") - used to know both range and unit |
| `default` | string | Default value with unit (e.g., "0.10 ms") - used for reset |
| `value_items` | string | Semicolon-separated list of possible values (quantized params only) |

### Parameter Name Prefixes

The `name` field includes prefixes to indicate automation and enabled status:

| Prefix | Meaning |
|---------|---------|
| `**name` | Automation active |
| `*/name` | Automation overridden |
| `name` | Normal, enabled |
| `*-name` | Disabled |

### Parameter Types

The metadata allows detection of parameter types:

#### 1. Continuous Parameters
```
Characteristics:
- value_items is empty string
- Has min/max/default values with units
- Example: Frequency, Volume, Pan

Value calculation:
- Use CC value to calculate actual value: value = min_numeric + (cc/127) * (max_numeric - min_numeric)
- Extract unit from min/max/default strings
- Display calculated value with unit
```

#### 2. Boolean Parameters
```
Characteristics:
- value_items has exactly 2 values separated by semicolon
- Example: "Off;On", "Disabled;Enabled"

Value calculation:
- CC value maps directly to index in value_items
- Display selected enum name from value_items
```

#### 3. Enum Parameters (Stepped)
```
Characteristics:
- value_items has more than 2 values separated by semicolon
- Example: "Saw;Square;Triangle;Sine"

Value calculation:
- CC value maps to index: index = round((cc/127) * (count-1))
- Display selected enum name from value_items
```

### Example Messages

#### Example 1: Analog Synth Parameters
```
SysEx 0x7D: "Frequency|20.0 Hz|20000.0 Hz|440.0 Hz||,Cutoff|20.0 Hz|20000.0 Hz|1000.0 Hz||,Resonance|0.0|10.0|0.0||,Detune|-100.0 st|100.0 st|0.0 st||,Shape|0|3|0|Saw;Square;Triangle;Sine|Square,Drive|0.0|10.0|0.0||,Volume|-inf|6.0|0.0||,Pan|-100.0|100.0|0.0||"
```
Parameters with units: Frequency (Hz), Cutoff (Hz), Detune (st), Volume (dB)
Parameters without units: Resonance, Drive, Pan

#### Example 2: Effect Device with Toggles
```
SysEx 0x7D: "Bypass|0.0|1.0|0.0|Off;On|,Enabled|0.0|1.0|1.0|Off;On|On,Quality|0.0|1.0|1.0|Low;High|High,Delay Time|0.01 s|10.0 s|0.50 s||,Feedback|0.0|100.0|30.0||,Mix|0.0|100.0|0.0||"
```
Parameters with units: Delay Time (s), Feedback (%), Mix (%)
Parameters without units: Bypass (boolean), Enabled (boolean), Quality (enum)

#### Example 3: Device with Automation (No Units)
```
SysEx 0x7D: "**Macro 1|0.0|1.0|0.5|,Macro 2|0.0|1.0|0.5|,*-Macro 3|0.0|1.0|0.5|,Macro 4|0.0|1.0|0.5|"
```
Macro controls typically don't have units - just display calculated value

#### Example 4: Drum Rack (Nested Device)
```
SysEx 0x7D: "Snr Decay|0.01 s|10.0 s|0.10 s||,Snr Tune|-24.0 st|24.0 st|0.0 st||,Kick Decay|0.01 s|10.0 s|0.10 s||,Kick Tune|-24.0 st|24.0 st|0.0 st||,HiHat Open|0.0|1.0|1.0|Off;On|On"
```
Parameters with units: Snr Tune (st = semitones), Kick Tune (st)
Parameters without units: Snr Decay, Kick Decay, HiHat Open (boolean)

#### Example 5: Filter Device with Actual Display Values
```
SysEx 0x7D: "Filter 1 Freq|20.0 Hz|20000.0 Hz|20000.0 Hz||,Filter 1 Res|0.0 %|125.0 %|0.0 %||,Filter 1 Drive|0.00 dB|24.0 dB|0.00 dB||,Filter 1 Type|0|4|0|Lowpass;Highpass;Bandpass;Notch;Morph|Lowpass"
```
Note: Filter 1 Res shows actual range 0.0%-125.0%, Filter 1 Drive shows 0.00 dB-24.0 dB (not normalized 0.0-1.0)

#### Example 6: Attack Parameter with ms Units
```
SysEx 0x7D: "Attack|0.10 ms|20.00 ms|0.10 ms||0.10 ms"
```
Note: min/max/default are full strings with units embedded - no need to extract unit separately!

### Value Calculation Examples

#### Continuous Parameter with Unit
```
Parameter: Frequency
Min: "20.0 Hz", Max: "20000.0 Hz", Default: "440.0 Hz", CC: 64
Extracted values: min=20.0, max=20000.0
Extracted unit: "Hz"
Calculation: 20.0 + (64/127) * (20000.0-20.0) = 10060.0
Display: "10060.0 Hz" (calculate value + unit from min/max/default)
```

#### Continuous Parameter without Unit
```
Parameter: Resonance
Min: "0.0", Max: "10.0", CC: 50
Extracted values: min=0.0, max=10.0
Extracted unit: nil
Calculation: 0.0 + (50/127) * (10.0-0.0) = 3.94
Display: "3.94" (no unit)
```

#### Filter Parameter with Actual Display Range
```
Parameter: Filter 1 Resonance
Min: "0.0 %", Max: "125.0 %", CC: 64
Extracted values: min=0.0, max=125.0
Extracted unit: "%"
Calculation: 0.0 + (64/127) * (125.0-0.0) = 62.99
Display: "63.0 %" or "63%"
```

#### Attack Parameter with ms Units
```
Parameter: Attack
Min: "0.10 ms", Max: "20.00 ms", Default: "0.10 ms", CC: 10
Extracted values: min=0.10, max=20.00
Extracted unit: "ms"
Calculation: 0.10 + (10/127) * (20.00-0.10) = 1.58
Display: "1.58 ms" (calculate value + unit from min/max/default)
Note: min/max/default are full strings with units embedded
```

#### Boolean Parameter
```
Parameter: Enabled
Value Items: "Off;On", CC: 64
Calculation: round((64/127) * (2-1)) = 1
Index 1 = "On"
Display: "On" (from value_items)
```

#### Enum Parameter
```
Parameter: Waveform
Value Items: "Saw;Square;Triangle;Sine", CC: 42
Calculation: round((42/127) * (4-1)) = 1
Index 1 = "Square"
Display: "Square" (from value_items)
```

### Implementation for iOS App

#### 1. Parse Parameter Metadata
Since min/max/default are now strings with units embedded, you can parse them differently:

```swift
struct ParameterMetadata {
    let name: String
    let min: String          // e.g., "0.10 ms", "0.0 %", "20.0 Hz"
    let max: String          // e.g., "20.00 ms", "125.0 %", "20000.0 Hz"
    let default: String       // e.g., "0.10 ms"
    let valueItems: [String]?  // nil for continuous, array for enums
}

func parseParameterMetadata(_ message: String) -> [ParameterMetadata] {
    let parameters = message.components(separatedBy: ",")

    for param in parameters {
        let fields = param.components(separatedBy: "|")
        guard fields.count == 5 else { continue }

        let name = fields[0]
        let min = fields[1]        // Full string with unit
        let max = fields[2]        // Full string with unit
        let default = fields[3]     // Full string with unit
        let valueItems = fields[4]

        let metadata = ParameterMetadata(
            name: name,
            min: min,
            max: max,
            default: default,
            valueItems: valueItems.isEmpty ? nil : valueItems.components(separatedBy: ";")
        )
    }
}
```

#### 2. Extract Unit from min/max/default
You can extract the unit from any of these fields (they all have units embedded):

```swift
func extractUnit(from displayString: String) -> String? {
    let parts = displayString.components(separatedBy: " ")
    if parts.count >= 2 {
        return parts.last
    }
    return nil
}

// All these will give you "ms":
let unit1 = extractUnit(from: "0.10 ms")   // from min
let unit2 = extractUnit(from: "20.00 ms")  // from max
let unit3 = extractUnit(from: "0.10 ms")   // from default
```

#### 3. Extract Numeric Value for Calculation
If you need to calculate values from CC, extract the numeric part:

```swift
func extractValue(from displayString: String) -> Double? {
    let parts = displayString.components(separatedBy: " ")
    return Double(parts.first ?? "")
}

// Example:
let minVal = extractValue(from: "0.10 ms")  // returns 0.10
let maxVal = extractValue(from: "20.00 ms")  // returns 20.00
```

#### 4. Display Value in Center of Dial
```swift
func displayValue(for encoder: Int, ccValue: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    if let valueItems = metadata.valueItems {
        // Enum/Boolean: display selected item name
        let index = Int(round(Double(ccValue) / 127.0 * Double(valueItems.count - 1)))
        let displayValue = valueItems[index]
        encoders[encoder].centerLabel.text = displayValue
    } else {
        // Continuous: calculate value and add unit from min/max/default
        let minVal = extractValue(from: metadata.min)!
        let maxVal = extractValue(from: metadata.max)!
        let actualValue = minVal + (Double(ccValue) / 127.0) * (maxVal - minVal)

        // Extract unit from min (or max/default)
        let unit = extractUnit(from: metadata.min)

        if let unit = unit {
            encoders[encoder].centerLabel.text = formatValue(actualValue, unit: unit)
        } else {
            encoders[encoder].centerLabel.text = formatValue(actualValue, unit: nil)
        }
    }
}

func formatValue(_ value: Double, unit: String?) -> String {
    let range = extractValue(from: metadata.max)! - extractValue(from: metadata.min)!

    // Format value with appropriate precision based on range
    var formattedValue: String
    if range < 10 {
        formattedValue = String(format: "%.2f", value)
    } else if range < 100 {
        formattedValue = String(format: "%.1f", value)
    } else {
        formattedValue = String(format: "%.0f", value)
    }

    // Add unit if available
    if let unit = unit {
        return "\(formattedValue) \(unit)"
    }
    return formattedValue
}
```

#### 5. Reset to Default
```swift
func resetToDefault(encoder: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    // Extract numeric values from display strings
    let minVal = extractValue(from: metadata.min)!
    let maxVal = extractValue(from: metadata.max)!
    let defaultVal = extractValue(from: metadata.default)!

    // Convert default value to CC
    let ccValue = Int(round((defaultVal - minVal) / (maxVal - minVal) * 127.0))
    sendMIDICC(encoder, value: ccValue)
}
```

#### 2. Extract Unit from min/max/default
You can extract the unit from any of these fields (they all have units embedded):

```swift
func extractUnit(from displayString: String) -> String? {
    let parts = displayString.components(separatedBy: " ")
    if parts.count >= 2 {
        return parts.last
    }
    return nil
}

// All these will give you "ms":
let unit1 = extractUnit(from: "0.10 ms")   // from min
let unit2 = extractUnit(from: "20.00 ms")  // from max
let unit3 = extractUnit(from: "0.10 ms")   // from default
let unit4 = extractUnit(from: "0.15 ms")  // from value_string
```

#### 3. Extract Numeric Value for Calculation
If you need to calculate values from CC, extract the numeric part:

```swift
func extractValue(from displayString: String) -> Double? {
    let parts = displayString.components(separatedBy: " ")
    return Double(parts.first ?? "")
}

// Example:
let minVal = extractValue(from: "0.10 ms")  // returns 0.10
let maxVal = extractValue(from: "20.00 ms")  // returns 20.00
```

#### 4. Display Value in Center of Dial
```swift
func displayValue(for encoder: Int, ccValue: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    if let valueItems = metadata.valueItems {
        // Enum/Boolean: display → selected item name
        let index = Int(round(Double(ccValue) / 127.0 * Double(valueItems.count - 1)))
        let displayValue = valueItems[index]
        encoders[encoder].centerLabel.text = displayValue
    } else {
        // Continuous: calculate value and add unit if available
        let minVal = extractValue(from: metadata.min)!
        let maxVal = extractValue(from: metadata.max)!
        let actualValue = minVal + (Double(ccValue) / 127.0) * (maxVal - minVal)

        // Use unit from any of the string fields
        let unit = extractUnit(from: metadata.valueString)

        if let unit = unit {
            encoders[encoder].centerLabel.text = formatValue(actualValue, unit: unit)
        } else {
            encoders[encoder].centerLabel.text = formatValue(actualValue, unit: nil)
        }
    }
}

func formatValue(_ value: Double, unit: String?) -> String {
    let range = extractValue(from: metadata.max)! - extractValue(from: metadata.min)!

    // Format value with appropriate precision based on range
    var formattedValue: String
    if range < 10 {
        formattedValue = String(format: "%.2f", value)
    } else if range < 100 {
        formattedValue = String(format: "%.1f", value)
    } else {
        formattedValue = String(format: "%.0f", value)
    }

    // Add unit if available
    if let unit = unit {
        return "\(formattedValue) \(unit)"
    }
    return formattedValue
}
```

#### 5. Reset to Default
```swift
func resetToDefault(encoder: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    // Extract numeric values from display strings
    let minVal = extractValue(from: metadata.min)!
    let maxVal = extractValue(from: metadata.max)!
    let defaultVal = extractValue(from: metadata.default)!

    // Convert default value to CC
    let ccValue = Int(round((defaultVal - minVal) / (maxVal - minVal) * 127.0))
    sendMIDICC(encoder, value: ccValue)
}
```

**Note**: Many parameters have empty `value_string`. This is expected - not all parameters provide formatted output. Extract the unit only when available. If unit is nil, display just the calculated numeric value.

#### 1. Parse Message
```swift
// Split by comma to get individual parameters
let parameters = message.components(separatedBy: ",")

// Split each parameter by pipe to get fields
for (index, param) in parameters.enumerated() {
    let fields = param.components(separatedBy: "|")
    guard fields.count == 6 else { continue }

    let name = fields[0]
    let min = Double(fields[1])!
    let max = Double(fields[2])!
    let default = Double(fields[3])!
    let valueItems = fields[4]  // Empty string for continuous
    let valueString = fields[5]

    // Extract unit from value_string if available
    let unit = extractUnit(from: valueString)

    // Store metadata for each encoder
    encoders[index].metadata = ParameterMetadata(
        name: name,
        min: min,
        max: max,
        default: default,
        valueItems: valueItems.isEmpty ? nil : valueItems.components(separatedBy: ";"),
        unit: unit
    )
}

func extractUnit(from valueString: String) -> String? {
    guard !valueString.isEmpty else { return nil }
    // Split by space and take the last part as unit
    let parts = valueString.components(separatedBy: " ")
    if parts.count >= 2 {
        return parts.last
    }
    return nil
}
```

#### 2. Display Value in Center of Dial
```swift
func displayValue(for encoder: Int, ccValue: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    if let valueItems = metadata.valueItems {
        // Enum/Boolean: display the selected item name
        let index = Int(round(Double(ccValue) / 127.0 * Double(valueItems.count - 1)))
        let displayValue = valueItems[index]
        encoders[encoder].centerLabel.text = displayValue
    } else {
        // Continuous: calculate value and add unit if available
        let actualValue = metadata.min + (Double(ccValue) / 127.0) * (metadata.max - metadata.min)
        encoders[encoder].centerLabel.text = formatValue(actualValue, unit: metadata.unit)
    }
}

func formatValue(_ value: Double, unit: String?) -> String {
    let range = metadata.max - metadata.min

    // Format value with appropriate precision based on range
    var formattedValue: String
    if range < 10 {
        formattedValue = String(format: "%.2f", value)
    } else if range < 100 {
        formattedValue = String(format: "%.1f", value)
    } else {
        formattedValue = String(format: "%.0f", value)
    }

    // Add unit if available
    if let unit = unit {
        return "\(formattedValue) \(unit)"
    }
    return formattedValue
}
```

#### 3. Reset to Default
```swift
func resetToDefault(encoder: Int) {
    guard let metadata = encoders[encoder].metadata else { return }

    // Convert default value to CC
    let ccValue = Int(round((metadata.default - metadata.min) / (metadata.max - metadata.min) * 127.0))
    sendMIDICC(encoder, value: ccValue)
}
```

### Special Value Handling

#### -inf (Negative Infinity)
Some parameters like volume may have `-inf` as minimum:
```
Volume|-inf|6|0||-2.5 dB
```

Handle this in your app:
```swift
let min = fields[1] == "-inf" ? -1000.0 : Double(fields[1])!
```

#### Boolean Values
For boolean parameters, min/max will be 0.0/1.0:
```
Enabled|0|1|0|Off;On|On
```

Map CC values to the two options directly.

#### Integer Values
Some parameters are integers (e.g., semitone detune):
```
Detune|-24|24|0||-12 st
```

Display as integer even though sent as float.

### When Messages Are Sent

Parameter metadata is sent in these situations:

1. **Device Selection**: When a device is selected
2. **Bank Navigation**: When using bank left/right buttons
3. **Mixer Toggle**: When switching between mixer and device views
4. **Connection**: On initial handshake and project send

### Message Size

The format uses strings for min/max/default (including units), which increases message size slightly:

**Typical message size**:
- 8 parameters × ~40-50 bytes = ~320-400 bytes
- Will likely exceed 240-byte limit and require chunking
- Chunking is handled automatically by _send_sys_ex_message

**Note**: String format with units ("0.10 ms") is larger than float format (0.10), but provides unit information directly without separate extraction.

### Testing

Test with various device types:

✅ **Analog Synth** (continuous + enum)
   - Frequency, Cutoff, Resonance, Waveform

✅ **Utility Device** (booleans)
   - Bypass, Enabled, Mono, Phase

✅ **EQ Device** (continuous with different ranges)
   - Low cut, High cut, Gain, Q

✅ **Reverb** (continuous with special values)
   - Size, Decay, Mix, Pre-delay

✅ **Compressor** (continuous + threshold)
   - Threshold, Ratio, Attack, Release

✅ **Instrument Rack** (nested parameters)
   - Macro controls, chain parameters

✅ **Drum Rack** (drum pad parameters)
   - Decay, Tune, Pitch, Pan

### Troubleshooting

#### No metadata received
- Check that device has parameters
- Verify device control is connected (not in mixer mode)
- Ensure parameter is mapped to encoder

#### min/max/default have different formats
Some parameters may have:
- Full strings with units: "0.10 ms", "20.00 ms" (best case)
- Normalized values: "0.0", "1.0" (fallback case)

Your app should handle both by extracting numeric value when needed for calculation.

#### Parsing errors
- Ensure you split by comma first (parameters), then pipe (fields)
- Handle empty value_items string for continuous parameters
- Handle special values like "-inf" in min/max/default strings
- Extract numeric part for CC-to-value calculations

#### Incorrect value displayed
- For continuous: calculate using formula: value = min_numeric + (cc/127) * (max_numeric-min_numeric)
  Where min_numeric/max_numeric are extracted from min/max strings
- For enums: round to nearest index in value_items array
- Display selected enum name, not to index
- Add unit extracted from min/max/default strings

#### Unit not displayed
- Extract unit by splitting any of min/max/default strings on space and taking last part
- If no unit available, display just to numeric value
- Example: "0.10 ms" → unit = "ms"
- Example: "0.0" (no space) → unit = nil

#### Default value seems wrong
Some parameters may have default values that differ from min:
- Check if default string matches min string (common for some parameters)
- If they differ, use default string for reset functionality
- Extract numeric value for CC calculation: `extractValue(from: default_string)`
```

---

**Last Updated**: 2026-03-03
**Version**: 1.9
**Script**: Tap.py
**Manufacturer ID**: 0x7D
