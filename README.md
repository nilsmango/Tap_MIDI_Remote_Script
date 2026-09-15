# Tap
Version: 2.1.0

An Ableton Live MIDI Remote Script for the iOS app 7III Tap by project7III.

More info: https://project7iii.com/tap

For troubleshooting and detailed instructions, see the [Tap User Manual](https://project7iii.com/tap/manual/#2-2-connect-your-iphone-or-ipad).

The app and Remote Script must be the same version. Install the current Remote Script before connecting Tap to Live.

## 1. Install the Tap MIDI Remote Script

1. Download and unzip `Tap.zip`.
2. Find the User Library location configured in Ableton Live. If you have not chosen a custom location, the defaults are:

   - **Windows:** `C:\Users\[username]\Documents\Ableton\User Library`
   - **macOS:** `~/Music/Ableton/User Library`

3. Inside that User Library, create a folder called `Remote Scripts` if it does not already exist. Place the unzipped folder called `Tap` into it.
4. Your directory should now look like this:

```
Ableton/
└── User Library/
    └── Remote Scripts/
        └── Tap/
            ├── tap_runtime.py
            ├── device_banks.py
            ├── tap_protocol.py
            ├── automation.py
            ├── Tap.py
            ├── __init__.py
            └── README.md (optional, can be removed)
```

> **Important:** The paths above are defaults, not requirements. If Live uses a custom User Library, use that location. Keep the folder names exactly `Remote Scripts` and `Tap` so Live can recognize the script.

Fully quit and reopen Live after installing or changing the Remote Script.

## 2. Connect your iPhone or iPad

For the most reliable connection, use a wired setup whenever possible. Tap needs MIDI in both directions, so the same active device or MIDI endpoint must be selected as both input and output in Live.

Before using either WiFi route, enable **MIDI over WiFi** in Tap's settings. Tap then exposes its Network MIDI session; connect to it from the computer's Network MIDI or rtpMIDI setup. If you never use Network MIDI, you can disable the setting.

For a direct one-to-one wireless connection, try Bluetooth MIDI before Network MIDI. Bluetooth MIDI connects directly without a WiFi router or Network MIDI session. Wireless performance still depends on distance and interference; use USB or wired MIDI for the most reliable connection in a dense Live Set.

### 2.1 macOS: Over USB-C

1. Connect your iPhone or iPad to your Mac with a data-capable USB-C cable. USB 2.0 is fast enough; a charge-only cable cannot create the MIDI connection.
2. Unlock the iPhone or iPad and open **Audio MIDI Setup** on the Mac.
3. Open **Window → Audio Devices** if that window is not already visible.
4. Find your iPhone or iPad in the sidebar and click **Enable**.
5. In Live, select the iPhone or iPad as both Tap input and output.

### 2.2 Windows: Wired MIDI interface setup

This is the recommended Windows setup. It is wired, bidirectional, and does not rely on WiFi.

The connection is:

```
iPhone/iPad
│ USB cable
USB-C MIDI interface with two MIDI cables
│ MIDI IN / MIDI OUT
CME H2MIDI Pro, H4MIDI WC, or another MIDI interface
│ USB cable
Windows PC with Ableton Live
```

1. Connect a USB-C MIDI interface to your iPhone or iPad.
2. Connect the CME H2MIDI Pro, CME H4MIDI WC, or another MIDI interface to your Windows computer via USB.
3. Connect **MIDI OUT** from the iPhone/iPad-side interface to **MIDI IN** on the Windows-side interface.
4. Connect **MIDI OUT** from the Windows-side interface to **MIDI IN** on the iPhone/iPad-side interface.
5. Open Tap and select the connected MIDI interface as MIDI input/output if needed.
6. In Live, select the Windows-side interface as both Tap input and output.

The iPhone or iPad remains the USB host for a class-compliant USB MIDI interface. The CME or other MIDI interface handles the Windows side.

### 2.3 Windows: Experimental direct USB MIDI host bridge

This setup may work, but it has not been tested by us.

1. Connect your iPhone or iPad to the **USB-A host port** of a CME H2MIDI Pro or CME H4MIDI WC.
2. Connect the interface's **USB-C computer port** to your Windows computer.
3. Open Tap and select the connected USB MIDI interface as MIDI input/output if needed.
4. In Live, select the CME interface as both Tap input and output.

This should work through USB MIDI virtual ports if the iPhone or iPad is recognized correctly by the CME USB host port. If it does not work, use the wired MIDI interface setup above.

### 2.4 macOS: Bluetooth MIDI

Bluetooth MIDI provides a direct, bidirectional wireless connection without a WiFi network. See [Apple's Bluetooth MIDI instructions](https://support.apple.com/en-ie/guide/audio-midi-setup/ams33f013765/mac) for the current Audio MIDI Setup workflow.

1. In Tap, open **Settings → Bluetooth MIDI**. Keep this panel available while making the first connection.
2. On your Mac, open **Audio MIDI Setup → Window → Show MIDI Studio**.
3. In MIDI Studio, choose **Configure Bluetooth**.
4. Select your iPhone or iPad and click **Connect**.
5. If it is not listed, return to Tap's Bluetooth MIDI panel and turn on **Advertise MIDI Service**, then look again on the Mac. Advertising is only needed while making Tap discoverable.
6. In Live, select the Bluetooth MIDI endpoint as both Tap input and output.

### 2.5 Windows: Bluetooth MIDI (experimental)

Windows Bluetooth MIDI support is experimental and has not been tested by us with Tap. Microsoft's [Windows MIDI Bluetooth Setup](https://microsoft.github.io/MIDI/tools/midibluetoothsetup/) is a separately installed preview and is not yet part of a normal consumer Windows release.

#### Windows MIDI Bluetooth Setup

1. In Tap, open **Settings → Bluetooth MIDI**. If Tap does not appear on Windows, turn on **Advertise MIDI Service**.
2. Open [Windows MIDI Bluetooth Setup](https://microsoft.github.io/MIDI/tools/midibluetoothsetup/) and connect to the iPhone or iPad.
3. Allow the connection if Windows asks.
4. In Live, select the new Bluetooth MIDI endpoint as both Tap input and output.

#### USB Bluetooth MIDI adapter

A USB Bluetooth MIDI adapter that supports Bluetooth **central** mode can connect to Tap and appear in Windows as a normal USB MIDI interface. The [CME WIDI Bud Pro](https://www.cme-pro.com/product/widi-bud-pro/) is one example. This setup has not been tested by us.

1. Connect the USB Bluetooth MIDI adapter to the Windows computer.
2. In Tap, open **Settings → Bluetooth MIDI** and make Tap discoverable if needed.
3. Pair the adapter with the iPhone or iPad according to the adapter's instructions.
4. In Live, select the adapter as both Tap input and output.

The adapter must support central mode. Two Bluetooth peripherals cannot initiate a connection to each other.

### 2.6 macOS: Over WiFi

If USB-C or Bluetooth MIDI is not available, use MIDI over WiFi on macOS. Use a clean, stable WiFi network and avoid busy public or shared networks.

1. Connect your iPhone or iPad to the same WiFi network as your Mac.
2. In Tap, enable **MIDI over WiFi** in **Settings**.
3. Follow [Apple's Network MIDI guide](https://support.apple.com/en-ca/guide/audio-midi-setup/ams1012/mac) to create or select the computer's Network MIDI session and connect Tap. You do not need to do **Step 9**.
4. In Live, select the Network MIDI endpoint as both Tap input and output.

### 2.7 Windows: rtpMIDI over ad hoc WiFi

If a wired or Bluetooth MIDI setup is not available, use a dedicated ad hoc WiFi network instead of a busy normal WiFi network.

1. Create an ad hoc WiFi network on your Windows computer.
2. Connect your iPhone or iPad to that WiFi network.
3. Download [rtpMIDI](https://www.tobias-erichsen.de/wp-content/uploads/2020/01/rtpMIDISetup_1_1_14_247.zip).
4. Open rtpMIDI on Windows and create a new session.
5. In Tap, enable **MIDI over WiFi** in **Settings**.
6. In rtpMIDI, add or connect the Tap Network MIDI endpoint as the session participant.
7. In Live, select the rtpMIDI session as both Tap input and output.

## 3. Set up Ableton Live

1. Launch Live.
2. Open Live's **Settings/Preferences** and choose **Link, Tempo & MIDI**.
3. Select the script `Tap` in the **Control Surface** column.
4. Select your active USB device, Bluetooth MIDI endpoint, MIDI interface, or Network Session as both **Input** and **Output** for Tap.
5. Activate **Track** and **Remote** for the active MIDI ports.
6. If you enable **MPE Pads** in Tap, also activate **MPE** for Tap's input port. Tap's green **MPE Remote Script Ready** message confirms script compatibility; it does not change Live's separate input-port switch.

Tap's **Test connection to Ableton Live** button helps identify where a connection stops:

- **No MIDI ports found:** check the data cable, MIDI interface, Bluetooth connection, or Network MIDI session.
- **One-way MIDI:** Tap can see only an input or output. It needs both.
- **Remote Script did not answer:** check the Tap Control Surface and its selected input and output in Live.
- **Wrong Remote Script version:** install the current Tap Remote Script.
- **Connection lost:** reconnect the cable or wireless MIDI route and test again.

The connection test still works after the free playing time has ended. It checks the setup without unlocking control of Live.

Tap sends MPE in the lower zone with channel 1 as the manager channel and channels 2–15 as member channels. Channel 16 remains reserved for the Tap control surface. Set MPE instruments and external hardware to a 48-semitone per-note pitch-bend range. Tap explicitly configures that range on every member channel.

Tap's **Track Controls Expression** setting chooses whether the expression encoder sends Slide (CC74, the default) or channel Pressure. Both can be changed while notes are playing.
