from __future__ import absolute_import, print_function, unicode_literals

from collections import namedtuple
from types import MappingProxyType


TapSysExMessageSpec = namedtuple(
    "TapSysExMessageSpec",
    (
        "manufacturer_id",
        "route",
        "family",
        "framing",
        "maximum_assembled_bytes",
        "direct_binary_record_width",
        "direct_binary_record_must_be_single",
        "includes_remote_device_byte",
    ),
)


def _tap_sysex_spec(
        manufacturer_id,
        route,
        family,
        framing="fixed",
        maximum_assembled_bytes=None,
        direct_binary_record_width=None,
        direct_binary_record_must_be_single=False,
        includes_remote_device_byte=False):
    return TapSysExMessageSpec(
        manufacturer_id,
        route,
        family,
        framing,
        maximum_assembled_bytes,
        direct_binary_record_width,
        direct_binary_record_must_be_single,
        includes_remote_device_byte,
    )


def _tap_sysex_registry(specs):
    registry = {}
    for spec in specs:
        if spec.manufacturer_id in registry:
            raise ValueError("Duplicate Tap SysEx manufacturer id")
        registry[spec.manufacturer_id] = spec
    return MappingProxyType(registry)


# Keep these v59 tables visibly mirrored with TapSysExRegistry in
# ProjectMIDI/Model/TapProtocol.swift. Numeric manufacturer IDs are overloaded
# across directions, so the registries must never be combined.
TAP_SYSEX_APP_TO_REMOTE_SPECS = (
    _tap_sysex_spec(0x09, "fireClip", "session"),
    _tap_sysex_spec(0x0A, "deleteClip", "session"),
    _tap_sysex_spec(0x0B, "copyClip", "session"),
    _tap_sysex_spec(0x0C, "scaleAndRoot", "selectedClip", "text"),
    _tap_sysex_spec(0x0D, "duplicateLoop", "selectedClip"),
    _tap_sysex_spec(0x0E, "addNotes", "selectedClip", "chunkedBinary", 262144, 11, True),
    _tap_sysex_spec(0x0F, "removeNotes", "selectedClip", "chunkedBinary", 262144, 5),
    _tap_sysex_spec(0x10, "modifyNotes", "selectedClip", "chunkedBinary", 524288, 16, True),
    _tap_sysex_spec(0x11, "clipMarker", "selectedClip", "binary"),
    _tap_sysex_spec(0x12, "visibleMixerRange", "session"),
    _tap_sysex_spec(0x13, "combineClips", "session"),
    _tap_sysex_spec(0x14, "setTrackArm", "session"),
    _tap_sysex_spec(0x15, "selectAdjacentClip", "selectedClip"),
    _tap_sysex_spec(0x16, "tempo", "session", "text"),
    _tap_sysex_spec(0x17, "metronome", "session"),
    _tap_sysex_spec(0x23, "setFollowAction", "session", "chunkedText", 65536),
    _tap_sysex_spec(0x24, "deleteFollowAction", "session", "chunkedText", 65536),
    _tap_sysex_spec(0x25, "requestFollowActions", "session"),
    _tap_sysex_spec(0x26, "stopTrackClips", "session"),
    _tap_sysex_spec(0x27, "highResolutionDeviceControl", "device", "binary"),
    _tap_sysex_spec(0x28, "mixerControl", "session", "binary"),
    _tap_sysex_spec(0x2B, "tapTempo", "session"),
    _tap_sysex_spec(0x2C, "toggleGroupFold", "session"),
    _tap_sysex_spec(0x2D, "addRandomEffect", "browser"),
    _tap_sysex_spec(0x2E, "setBrowserInsertTarget", "browser"),
    _tap_sysex_spec(0x2F, "moveDevice", "device"),
    _tap_sysex_spec(0x30, "rackSnapshot", "device"),
    _tap_sysex_spec(0x31, "requestAutomationEnvelope", "automation", "chunkedText", 1048576),
    _tap_sysex_spec(0x32, "writeAutomationEnvelope", "automation", "chunkedMixed", 1048576),
    _tap_sysex_spec(0x33, "setDecoupledAutomationLength", "automation", "chunkedText", 65536),
    _tap_sysex_spec(0x34, "unfoldDecoupledAutomation", "automation"),
    _tap_sysex_spec(0x35, "clearAutomationEnvelope", "automation"),
    _tap_sysex_spec(0x36, "clearAllAutomationEnvelopes", "automation"),
    _tap_sysex_spec(0x37, "setMutatorClip", "mutator", "chunkedText", 262144),
    _tap_sysex_spec(0x38, "finishMutatorClip", "mutator"),
    _tap_sysex_spec(0x39, "updateMutatorSettings", "mutator", "chunkedText", 262144),
    _tap_sysex_spec(0x3A, "replaceRhythmLane", "mutator", "chunkedText", 262144),
    _tap_sysex_spec(0x3B, "requestTrackLocalControls", "expression"),
    _tap_sysex_spec(0x3C, "browserSearch", "browser", "chunkedText", 262144),
    _tap_sysex_spec(0x3D, "browserPreview", "browser"),
    _tap_sysex_spec(0x3E, "flin", "mutator", "chunkedText", 262144),
    _tap_sysex_spec(0x43, "simplerAction", "device"),
    _tap_sysex_spec(0x45, "requestSimplerWaveform", "device"),
    _tap_sysex_spec(0x46, "setSimplerViewport", "device"),
    _tap_sysex_spec(0x47, "setClipPositionFeedback", "session"),
    _tap_sysex_spec(0x4B, "noteRepeat", "expression"),
    _tap_sysex_spec(0x4F, "selectTrackExpressionControl", "expression"),
    _tap_sysex_spec(0x52, "audioClip", "audioClip", "chunkedText", 524288),
    _tap_sysex_spec(0x54, "browserJumpToPage", "browser"),
    _tap_sysex_spec(0x55, "wideSession", "session"),
    _tap_sysex_spec(0x5A, "beginNoteAddTransaction", "selectedClip"),
    _tap_sysex_spec(0x5C, "nativeNoteTransfer", "selectedClip", "chunkedBinary", 524288),
    _tap_sysex_spec(0x60, "grooveEdit", "groove", "chunkedText", 65536),
    _tap_sysex_spec(0x62, "grooveFocus", "groove"),
    _tap_sysex_spec(0x65, "eqEightVisualizationEdit", "device", "binary"),
)
TAP_SYSEX_APP_TO_REMOTE = _tap_sysex_registry(TAP_SYSEX_APP_TO_REMOTE_SPECS)

TAP_SYSEX_REMOTE_TO_APP_SPECS = (
    _tap_sysex_spec(0x01, "devices", "device", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x02, "tracks", "session", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x03, "selectedTrack", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x04, "trackColors", "session", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x05, "clipSlots", "session", "chunkedText", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x06, "returnTracks", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x07, "returnTrackColors", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x08, "selectedReturnTrack", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x0A, "scaleAndRoot", "selectedClip", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x0B, "selectedTrackMidiCapability", "selectedClip", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x0C, "trackStatus", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x0D, "selectedClipNotes", "selectedClip", "chunkedBinary", 1048576, includes_remote_device_byte=True),
    _tap_sysex_spec(0x0E, "selectedClipMetadata", "selectedClip", "chunkedBinary", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x0F, "selectedClipPlayingPosition", "selectedClip", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x10, "selectedClip", "selectedClip", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x11, "drumPadNames", "device", "chunkedText", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x12, "tempo", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x13, "browser", "browser", "chunkedText", 1048576, includes_remote_device_byte=True),
    _tap_sysex_spec(0x17, "metronome", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x18, "followActions", "session", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x28, "deviceParameterLiveValue", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x29, "reEnableAutomation", "automation", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x2A, "mixerAutomationStatus", "automation", "chunkedText", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x2B, "groupFoldStates", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x2D, "groupFoldVisibility", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x30, "rackSnapshot", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x31, "automationEnvelope", "automation", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x3B, "trackLocalControls", "expression", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x3E, "browserSearchProgress", "browser", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x41, "simplerWaveform", "device", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x42, "simplerState", "device", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x44, "simplerAction", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x47, "clipPlayingPositions", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x48, "simplerSliceState", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x49, "visualFeedback", "device", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x4A, "meldEngine", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x4C, "noteRepeat", "expression", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x4D, "deviceName", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x4E, "mpeAvailability", "expression", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x50, "audioClipState", "audioClip", "chunkedText", 524288, includes_remote_device_byte=True),
    _tap_sysex_spec(0x51, "audioClipWaveform", "audioClip", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x53, "audioClipAction", "audioClip", "chunkedText", 65536, includes_remote_device_byte=True),
    _tap_sysex_spec(0x55, "clipSlotDelta", "session", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x56, "projectSnapshotControl", "session", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x57, "audioClipPlayback", "audioClip", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x5B, "noteAddResult", "selectedClip", "chunkedText", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x5D, "bankList", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x60, "groovePool", "groove", "chunkedText", 262144, includes_remote_device_byte=True),
    _tap_sysex_spec(0x61, "grooveEditResult", "groove", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x64, "eqEightVisualization", "device", "binary", includes_remote_device_byte=True),
    _tap_sysex_spec(0x6D, "currentBank", "device", "text", includes_remote_device_byte=True),
    _tap_sysex_spec(0x7D, "parameterMetadata", "device", "chunkedText", 262144, includes_remote_device_byte=True),
)
TAP_SYSEX_REMOTE_TO_APP = _tap_sysex_registry(TAP_SYSEX_REMOTE_TO_APP_SPECS)
