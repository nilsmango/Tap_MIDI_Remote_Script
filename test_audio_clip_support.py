import ast
import os
import pathlib
import re
import types
import unittest
from urllib.parse import unquote, urlparse


SOURCE = pathlib.Path(__file__).with_name("Tap.py")
METHOD_NAMES = {
    "_audio_clip_float",
    "_audio_clip_warp_mode_label",
    "_audio_clip_warp_markers_payload",
    "_audio_clip_sample_duration",
    "_audio_clip_sample_end",
    "_send_audio_clip_waveform",
    "_audio_clip_navigation_availability",
    "_select_adjacent_audio_clip",
    "_send_all_drum_pad_names",
    "_sync_drum_rack_device",
    "_set_simpler_device",
    "_send_audio_clip_state",
    "_set_audio_clip_property",
    "_set_audio_clip_pitch",
    "_set_audio_clip_one",
    "_edit_audio_clip_warp_marker",
    "_warp_audio_clip_to_grid",
    "_convert_selected_audio_clip",
    "_refresh_audio_conversion",
    "_handle_audio_clip_command",
    "_browser_item_file_path",
    "_load_browser_item_into_audio_clip",
    "_browser_load_item",
    "_browser_jump_to_page",
}


class WarpMode:
    beats = 0
    tones = 1
    texture = 2
    repitch = 3
    complex = 4
    complex_pro = 5


class WarpMarkerSpec:
    def __init__(self, beat_time, sample_time):
        self.beat_time = beat_time
        self.sample_time = sample_time


class AudioToMidiType:
    harmony_to_midi = "harmony"
    melody_to_midi = "melody"
    drums_to_midi = "drums"


class ConversionSpy:
    AudioToMidiType = AudioToMidiType

    def __init__(self):
        self.calls = []

    def create_midi_track_with_simpler(self, song, clip):
        self.calls.append(("simpler", song, clip))

    def create_drum_rack_from_audio_clip(self, song, clip):
        self.calls.append(("drum_pad", song, clip))

    def is_convertible_to_midi(self, song, clip):
        self.calls.append(("can_convert", song, clip))
        return True

    def audio_to_midi_clip(self, song, clip, conversion_type):
        self.calls.append(("audio_to_midi", song, clip, conversion_type))


CONVERSIONS = ConversionSpy()
Live = types.SimpleNamespace(
    Clip=types.SimpleNamespace(WarpMode=WarpMode, WarpMarker=WarpMarkerSpec),
    Conversions=CONVERSIONS,
)


def extracted_methods():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    tap_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Tap")
    methods = [
        node for node in tap_class.body
        if isinstance(node, ast.FunctionDef) and node.name in METHOD_NAMES
    ]
    assert {node.name for node in methods} == METHOD_NAMES
    module = ast.Module(body=methods, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "Live": Live,
        "liveobj_valid": lambda value: value is not None,
        "os": os,
        "re": re,
        "unquote": unquote,
        "urlparse": urlparse,
    }
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return {name: namespace[name] for name in METHOD_NAMES}


class Marker:
    def __init__(self, beat_time, sample_time):
        self.beat_time = beat_time
        self.sample_time = sample_time


class Clip:
    is_audio_clip = True
    is_midi_clip = False
    is_recording = False
    name = "Kick | bright"
    looping = True
    warping = False
    warp_mode = 0
    available_warp_modes = (0, 1, 5)
    gain = 0.75
    gain_display_string = "-2.50 dB"
    pitch_coarse = 3
    pitch_fine = -7
    ram_mode = True
    muted = False
    legato = True
    launch_mode = 2
    launch_quantization = 12
    start_marker = 0.25
    end_marker = 3.5
    loop_start = 0.5
    loop_end = 2.5
    sample_length = 48000 * 3.5
    sample_rate = 48000
    is_playing = False
    playing_position = 1.25
    warp_markers = (Marker(0, 0.25), Marker(4, 3.5))
    signature_numerator = 7
    signature_denominator = 8

    def crop(self):
        pass

    def add_warp_marker(self, marker):
        assert isinstance(marker, WarpMarkerSpec)
        self.added_warp_marker = marker
        beat_time = float(marker.beat_time)
        markers = list(self.warp_markers)
        markers.insert(-1, Marker(beat_time, marker.sample_time))
        self.warp_markers = tuple(sorted(markers, key=lambda item: item.beat_time))

    def beat_to_sample_time(self, beat_time):
        return float(beat_time) * self.sample_rate

    def sample_to_beat_time(self, _):
        raise AssertionError("private frame-based converter must not be used")

    def move_warp_marker(self, beat_time, distance):
        marker = next(item for item in self.warp_markers if item.beat_time == beat_time)
        marker.beat_time += distance

    def remove_warp_marker(self, beat_time):
        self.warp_markers = tuple(
            item for item in self.warp_markers
            if item.beat_time != beat_time
        )


class ClipSlot:
    def __init__(self, clip=None):
        self.clip = clip
        self.has_clip = clip is not None
        self.is_playing = False
        self.is_triggered = False
        self.fire_calls = 0
        self.stop_calls = 0

    def fire(self):
        self.fire_calls += 1
        self.is_triggered = True

    def stop(self):
        self.stop_calls += 1
        self.is_playing = False
        self.is_triggered = False

    def create_audio_clip(self, _):
        self.clip = Clip()
        self.has_clip = True


class Track:
    def __init__(self, slots):
        self.clip_slots = slots
        self.devices = []
        self.view = types.SimpleNamespace(selected_device=None)


class Song:
    def __init__(self, track):
        self.tracks = [track]
        self.scenes = [object() for _ in track.clip_slots]
        self.view = types.SimpleNamespace(
            selected_track=track,
            selected_scene=self.scenes[1],
            highlighted_clip_slot=track.clip_slots[1],
        )


class Browser:
    def __init__(self, song):
        self.song = song
        self.loaded = []
        self.hotswap_target = None

    def load_item_into_selected_clipslot(self, item):
        self.loaded.append(item)
        slot = self.song.view.highlighted_clip_slot
        slot.clip = Clip()
        slot.has_clip = True

    def load_item(self, item):
        self.loaded.append(item)


class PublicBrowser:
    def __init__(self, song):
        self.song = song
        self.loaded = []

    def load_item(self, item):
        self.loaded.append(item)
        slot = self.song.view.highlighted_clip_slot
        slot.clip = Clip()
        slot.has_clip = True


class Harness:
    def __init__(self):
        self.clip = Clip()
        self.slots = [ClipSlot(Clip()), ClipSlot(self.clip), ClipSlot(Clip())]
        self.track = Track(self.slots)
        self.song_state = Song(self.track)
        self.browser = Browser(self.song_state)
        self.sent = []
        self.results = []
        self._last_audio_clip_state = None
        self._last_audio_clip_action_result = None
        self._audio_clip_waveform_generation = 0
        self._simpler_waveform_cache = {}
        self.browser_audio_clip_target = None
        self.browser_drum_pad_target = None
        self.browser_insert_after_device_index = None
        self.browser_current_items = []
        self.browser_current_page = 0
        self.browser_items_per_page = 12
        self.browser_pages_count = 0
        self.browser_page_requests = []
        self._simpler_device = None
        self._simpler_waveform_generation = 0
        self.audio_clip_listener_removals = 0

    def song(self):
        return self.song_state

    def application(self):
        return types.SimpleNamespace(browser=self.browser)

    def _selected_audio_clip_context(self, include_empty=False):
        slot = self.song_state.view.highlighted_clip_slot
        scene_index = self.track.clip_slots.index(slot)
        return (slot, slot.clip if slot.has_clip else None, 0, scene_index)

    def _connect_audio_clip_listeners(self, slot, clip):
        self.connected = clip
        return False

    def _request_audio_clip_waveform(self):
        self.waveform_requested = True

    def _send_binary_sys_ex_message(self, values, manufacturer_id):
        self.sent.append((manufacturer_id, tuple(values)))

    def _send_sys_ex_message(self, payload, manufacturer_id):
        self.sent.append((manufacturer_id, payload))

    def _escape_sysex_string(self, value):
        result = str(value).replace("\\", "\\\\")
        for character in "|;":
            result = result.replace(character, "\\" + character)
        return result

    def _unescape_sysex_string(self, value):
        result = ""
        escaping = False
        for character in value:
            if escaping:
                result += character
                escaping = False
            elif character == "\\":
                escaping = True
            else:
                result += character
        return result

    def _split_escaped_sysex_fields(self, value, separator):
        fields, current, escaping = [], "", False
        for character in value:
            if escaping:
                current += "\\" + character
                escaping = False
            elif character == "\\":
                escaping = True
            elif character == separator:
                fields.append(current)
                current = ""
            else:
                current += character
        fields.append(current)
        return fields

    def _send_audio_clip_action_result(self, action, succeeded, message):
        self.results.append((action, succeeded, message))

    def _send_selected_clip_slot(self, index):
        self.selected_clip_slot = index

    def schedule_message(self, _, callback):
        callback()

    def _on_tracks_changed(self):
        self.tracks_changed = True

    def _on_device_changed(self):
        self.device_changed = True

    def _on_selected_track_changed(self):
        self.selected_track_changed = True

    def _find_drum_rack_in_track(self, track):
        return next(
            (
                device for device in getattr(track, "devices", ())
                if bool(getattr(device, "can_have_drum_pads", False))
            ),
            None,
        )

    def _is_simpler_device(self, _):
        return False

    def _remove_simpler_listeners(self):
        pass

    def _disconnect_simpler_decorator(self):
        pass

    def _remove_audio_clip_listeners(self):
        self.audio_clip_listener_removals += 1

    def _send_simpler_waveform_clear(self):
        pass

    def _send_simpler_playhead(self, **_):
        pass

    def _send_browser_page(self, page):
        self.browser_page_requests.append(page)

    def _remove_drum_pad_name_listeners(self):
        self.drum_listener_removals = getattr(self, "drum_listener_removals", 0) + 1

    def _setup_drum_pad_listeners(self):
        self.drum_listener_setups = getattr(self, "drum_listener_setups", 0) + 1


for method_name, method in extracted_methods().items():
    setattr(Harness, method_name, method)


class AudioClipSupportTests(unittest.TestCase):
    def setUp(self):
        CONVERSIONS.calls.clear()
        self.harness = Harness()

    def test_state_preserves_unwarped_seconds_and_escapes_name(self):
        self.harness._send_audio_clip_state(force=True)
        manufacturer_id, payload = self.harness.sent[-1]
        self.assertEqual(manufacturer_id, 0x50)
        self.assertTrue(payload.startswith("2|audio|"))
        self.assertIn("Kick \\| bright", payload)
        self.assertIn("|seconds|", payload)
        self.assertIn("|168000.0|48000.0|3.5|3.5|seconds|", payload)
        self.assertIn("0:Beats;1:Tones;5:Complex Pro", payload)
        fields = [
            self.harness._unescape_sysex_string(value)
            for value in self.harness._split_escaped_sysex_fields(payload, "|")
        ]
        self.assertEqual(len(fields), 41)
        self.assertEqual(fields[4], "Kick | bright")
        self.assertEqual(fields[19:25], ["3.5", "3.5", "seconds", "0", "0", "1.25"])
        self.assertEqual(fields[32], "7:8")
        self.assertEqual(fields[33], "0")
        self.assertEqual(fields[34:36], ["1", "1"])
        self.assertEqual(fields[36:41], ["1", "0", "1", "2", "12"])

    def test_non_simpler_device_refresh_keeps_audio_clip_listener(self):
        self.harness._set_simpler_device(object())
        self.assertEqual(self.harness.audio_clip_listener_removals, 0)

    def test_unchanged_drum_rack_is_resent_on_reconnect_refresh(self):
        rack = object()
        self.harness._drum_rack_device = rack
        self.harness._sync_drum_rack_device(rack)
        self.assertEqual(self.harness.drum_listener_setups, 1)
        self.assertEqual(getattr(self.harness, "drum_listener_removals", 0), 0)

    def test_accelerated_browser_hold_requests_only_the_final_clamped_page(self):
        self.harness.browser_pages_count = 1_250
        self.harness._browser_jump_to_page([0x7F, 0x7F, 0x7F])
        self.assertEqual(self.harness.browser_page_requests, [1_249])

        self.harness.browser_page_requests = []
        self.harness._browser_jump_to_page([103, 7, 0])
        self.assertEqual(self.harness.browser_page_requests, [999])

    def test_state_switches_to_beats_when_warped(self):
        self.harness.clip.warping = True
        self.harness._send_audio_clip_state(force=True)
        self.assertIn("|beats|", self.harness.sent[-1][1])
        self.assertIn("|3.5|4.0|beats|", self.harness.sent[-1][1])
        fields = self.harness._split_escaped_sysex_fields(self.harness.sent[-1][1], "|")
        self.assertEqual(fields[31], "0.000000:0.250000:0;4.000000:3.500000:1")

    def test_warp_marker_payload_keeps_the_shadow_marker_for_long_clips(self):
        self.harness.clip.warping = True
        self.harness.clip.warp_markers = tuple(
            Marker(float(index), float(index) / 10.0)
            for index in range(100)
        )
        payload = self.harness._audio_clip_warp_markers_payload(self.harness.clip)
        markers = payload.split(";")
        self.assertEqual(len(markers), 64)
        self.assertTrue(markers[-1].startswith("99.000000:9.900000:"))
        self.assertTrue(markers[-1].endswith(":1"))

    def test_audio_waveform_reduction_uses_the_complete_file(self):
        peaks = [0] * 511 + [100]
        self.harness._send_audio_clip_waveform(0, peaks)
        manufacturer_id, payload = self.harness.sent[-1]
        self.assertEqual(manufacturer_id, 0x51)
        self.assertEqual(len(payload), 114)
        self.assertEqual(payload[-1], 100)

    def test_add_move_and_remove_warp_markers(self):
        self.harness.clip.warping = True
        add = [0xF0, 0x52] + list(b"addWarpMarker|2") + [0xF7]
        self.harness._handle_audio_clip_command(add)
        self.assertTrue(any(marker.beat_time == 2 for marker in self.harness.clip.warp_markers))
        self.assertIsInstance(self.harness.clip.added_warp_marker, WarpMarkerSpec)
        self.assertEqual(self.harness.clip.added_warp_marker.sample_time, 2)

        move = [0xF0, 0x52] + list(b"moveWarpMarker|2|3") + [0xF7]
        self.harness._handle_audio_clip_command(move)
        self.assertTrue(any(marker.beat_time == 3 for marker in self.harness.clip.warp_markers))

        remove = [0xF0, 0x52] + list(b"removeWarpMarker|3") + [0xF7]
        self.harness._handle_audio_clip_command(remove)
        self.assertFalse(any(marker.beat_time == 3 for marker in self.harness.clip.warp_markers))

    def test_move_and_remove_resolve_rounded_marker_timestamp(self):
        self.harness.clip.warping = True
        precise = Marker(2.1234564, 2.0)
        self.harness.clip.warp_markers = (
            self.harness.clip.warp_markers[0],
            precise,
            self.harness.clip.warp_markers[-1],
        )
        move = [0xF0, 0x52] + list(b"moveWarpMarker|2.123456|3") + [0xF7]
        self.harness._handle_audio_clip_command(move)
        self.assertAlmostEqual(precise.beat_time, 3)

        remove = [0xF0, 0x52] + list(b"removeWarpMarker|3.000000") + [0xF7]
        self.harness._handle_audio_clip_command(remove)
        self.assertNotIn(precise, self.harness.clip.warp_markers)

    def test_waveform_playback_scrub_commands_are_rejected(self):
        scrub = [0xF0, 0x52] + list(b"scrub|1") + [0xF7]
        self.harness._handle_audio_clip_command(scrub)
        self.assertEqual(self.harness.results[-1][0], "scrub")
        self.assertFalse(self.harness.results[-1][1])

    def test_state_refresh_does_not_resend_the_waveform(self):
        self.harness._send_audio_clip_state(force=True)
        self.assertFalse(hasattr(self.harness, "waveform_requested"))
        self.harness._send_audio_clip_state(force=True, request_waveform=True)
        self.assertTrue(self.harness.waveform_requested)

    def test_crop_remains_available_while_clip_is_playing(self):
        self.harness.slots[1].is_playing = True
        self.harness._send_audio_clip_state(force=True)
        fields = [
            self.harness._unescape_sysex_string(value)
            for value in self.harness._split_escaped_sysex_fields(self.harness.sent[-1][1], "|")
        ]
        self.assertEqual(fields[25], "1")

    def test_property_clamps_and_rejects_unavailable_warp_mode(self):
        self.harness._set_audio_clip_property(self.harness.clip, "gain", "3")
        self.assertEqual(self.harness.clip.gain, 1.0)
        self.harness._set_audio_clip_property(self.harness.clip, "pitch_coarse", "-99")
        self.assertEqual(self.harness.clip.pitch_coarse, -48)
        self.harness._set_audio_clip_property(self.harness.clip, "ram_mode", "0")
        self.assertFalse(self.harness.clip.ram_mode)
        self.harness._set_audio_clip_property(self.harness.clip, "legato", "1")
        self.assertTrue(self.harness.clip.legato)
        self.harness._set_audio_clip_property(self.harness.clip, "launch_mode", "99")
        self.assertEqual(self.harness.clip.launch_mode, 3)
        self.harness._set_audio_clip_property(self.harness.clip, "launch_quantization", "99")
        self.assertEqual(self.harness.clip.launch_quantization, 14)
        with self.assertRaises(ValueError):
            self.harness._set_audio_clip_property(self.harness.clip, "warp_mode", "4")

    def test_pitch_command_updates_coarse_and_fine_as_one_value(self):
        message = [0xF0, 0x52] + list(b"setPitch|-4|50") + [0xF7]
        self.harness._handle_audio_clip_command(message)

        self.assertEqual(self.harness.clip.pitch_coarse, -4)
        self.assertEqual(self.harness.clip.pitch_fine, 50)
        self.assertFalse(self.harness._audio_clip_pitch_update_in_progress)

        fields = [
            self.harness._unescape_sysex_string(value)
            for value in self.harness._split_escaped_sysex_fields(self.harness.sent[-1][1], "|")
        ]
        self.assertEqual(fields[11:13], ["-4", "50"])

    def test_pitch_command_clamps_both_parts_together(self):
        message = [0xF0, 0x52] + list(b"setPitch|-99|99") + [0xF7]
        self.harness._handle_audio_clip_command(message)

        self.assertEqual(self.harness.clip.pitch_coarse, -48)
        self.assertEqual(self.harness.clip.pitch_fine, 50)

    def test_existing_pitch_properties_remain_editable_while_playing(self):
        self.harness.clip.is_playing = True

        coarse = [0xF0, 0x52] + list(b"set|pitch_coarse|-12") + [0xF7]
        fine = [0xF0, 0x52] + list(b"set|pitch_fine|37") + [0xF7]
        self.harness._handle_audio_clip_command(coarse)
        self.harness._handle_audio_clip_command(fine)

        self.assertEqual(self.harness.clip.pitch_coarse, -12)
        self.assertEqual(self.harness.clip.pitch_fine, 37)

    def test_marker_domain_uses_full_sample_and_position_preserves_loop_move(self):
        self.harness._set_audio_clip_property(self.harness.clip, "end_marker", "99")
        self.assertEqual(self.harness.clip.end_marker, 3.5)
        self.harness._set_audio_clip_property(self.harness.clip, "position", "1")
        self.assertEqual(self.harness.clip.position, 1.0)

    def test_warp_to_grid_reports_when_live_does_not_expose_it(self):
        with self.assertRaisesRegex(RuntimeError, "private Push operation"):
            self.harness._warp_audio_clip_to_grid(self.harness.clip)

    def test_all_conversion_routes_call_live_conversions(self):
        for conversion in ("simpler", "drum_pad", "harmony", "melody", "drums"):
            self.harness._convert_selected_audio_clip(conversion)
        call_names = [call[0] for call in CONVERSIONS.calls]
        self.assertIn("simpler", call_names)
        self.assertIn("drum_pad", call_names)
        self.assertEqual(call_names.count("audio_to_midi"), 3)

    def test_conversion_command_is_deferred_and_reports_start(self):
        message = [0xF0, 0x52] + list(b"convert|melody") + [0xF7]
        self.harness._handle_audio_clip_command(message)
        self.assertIn(("audio_to_midi", self.harness.song_state, self.harness.clip, "melody"), CONVERSIONS.calls)
        self.assertEqual(self.harness.results[-1], ("convert", True, "Conversion started"))

    def test_drum_conversion_refresh_selects_occupied_pad(self):
        occupied_pad = types.SimpleNamespace(chains=(object(),), name="", note=36)
        empty_pad = types.SimpleNamespace(chains=(), name="", note=37)
        rack = types.SimpleNamespace(
            can_have_drum_pads=True,
            drum_pads=[occupied_pad, empty_pad],
            view=types.SimpleNamespace(selected_drum_pad=None),
        )
        converted_track = Track([])
        converted_track.devices = [rack]
        self.harness.song_state.tracks.append(converted_track)
        self.harness._refresh_audio_conversion(
            (self.harness.track,),
            "drum_pad",
        )
        self.assertIs(self.harness.song_state.view.selected_track, converted_track)
        self.assertIs(rack.view.selected_drum_pad, occupied_pad)
        self.assertTrue(self.harness.selected_track_changed)
        self.assertIn((0x11, "36,Pad 36"), self.harness.sent)

    def test_browse_command_records_exact_empty_slot_target(self):
        message = [0xF0, 0x52] + list(b"browse|4|9") + [0xF7]
        self.harness._handle_audio_clip_command(message)
        self.assertEqual(self.harness.browser_audio_clip_target, (4, 9))
        self.assertEqual(self.harness.results[-1], ("browse", True, "Choose a sample"))

    def test_virtual_browser_sample_uses_live_selected_clip_slot_loader(self):
        empty_slot = ClipSlot()
        self.harness.track.clip_slots[1] = empty_slot
        self.harness.song_state.view.highlighted_clip_slot = empty_slot
        item = types.SimpleNamespace(uri="query:PackSample", name="Pack Sample.wav")
        loaded_slot = self.harness._load_browser_item_into_audio_clip(item, 0, 1)
        self.assertIs(loaded_slot, empty_slot)
        self.assertTrue(empty_slot.has_clip)
        self.assertEqual(self.harness.browser.loaded, [item])

    def test_virtual_browser_sample_falls_back_to_public_load_item(self):
        empty_slot = ClipSlot()
        self.harness.track.clip_slots[1] = empty_slot
        self.harness.song_state.view.highlighted_clip_slot = empty_slot
        self.harness.browser = PublicBrowser(self.harness.song_state)
        item = types.SimpleNamespace(uri="query:PackSample", name="Pack Sample.wav")
        self.harness._load_browser_item_into_audio_clip(item, 0, 1)
        self.assertTrue(empty_slot.has_clip)
        self.assertEqual(self.harness.browser.loaded, [item])

    def test_browser_sample_hotswaps_into_targeted_empty_drum_pad(self):
        item = types.SimpleNamespace(uri="query:PackSample", name="Pack Sample.wav")
        pad = types.SimpleNamespace(chains=())
        self.harness.browser_current_items = [item]
        self.harness.browser_drum_pad_target = pad
        self.harness._browser_load_item(1)
        self.assertEqual(self.harness.browser.loaded, [item])
        self.assertIsNone(self.harness.browser.hotswap_target)
        self.assertEqual(
            self.harness.results[-1],
            ("load", True, "Sample loaded to Drum Rack pad"),
        )

    def test_drum_pad_browser_enters_hotswap_before_listing_items(self):
        pad = types.SimpleNamespace(chains=())
        rack = types.SimpleNamespace(
            can_have_drum_pads=True,
            drum_pads=[pad],
            view=types.SimpleNamespace(selected_drum_pad=None),
        )
        self.harness._drum_rack_device = rack
        browse = [0xF0, 0x52] + list(b"browseDrumPad|0") + [0xF7]
        self.harness._handle_audio_clip_command(browse)
        self.assertIs(rack.view.selected_drum_pad, pad)
        self.assertIs(self.harness.browser.hotswap_target, pad)
        self.assertIs(self.harness.browser_drum_pad_target, pad)

    def test_drum_pad_browser_can_replace_an_occupied_pad(self):
        pad = types.SimpleNamespace(chains=(object(),))
        rack = types.SimpleNamespace(
            can_have_drum_pads=True,
            drum_pads=[pad],
            view=types.SimpleNamespace(selected_drum_pad=None),
        )
        self.harness._drum_rack_device = rack
        browse = [0xF0, 0x52] + list(b"browseDrumPad|0") + [0xF7]
        self.harness._handle_audio_clip_command(browse)
        self.assertIs(rack.view.selected_drum_pad, pad)
        self.assertIs(self.harness.browser.hotswap_target, pad)
        self.assertEqual(
            self.harness.results[-1],
            ("browseDrumPad", True, "Choose a Drum Pad replacement"),
        )

    def test_play_stop_and_adjacent_selection_are_direct(self):
        slot = self.harness.song_state.view.highlighted_clip_slot
        play_message = [0xF0, 0x52] + list(b"play") + [0xF7]
        self.harness._handle_audio_clip_command(play_message)
        self.assertEqual(slot.fire_calls, 1)
        self.assertTrue(slot.is_triggered)

        stop_message = [0xF0, 0x52] + list(b"stop") + [0xF7]
        self.harness._handle_audio_clip_command(stop_message)
        self.assertEqual(slot.stop_calls, 1)
        self.assertFalse(slot.is_triggered)

        self.harness._select_adjacent_audio_clip("next")
        self.assertIs(self.harness.song_state.view.highlighted_clip_slot, self.harness.slots[2])
        self.assertEqual(self.harness.selected_clip_slot, 2)

    def test_adjacent_audio_navigation_can_select_an_empty_slot(self):
        empty_slot = ClipSlot()
        self.harness.track.clip_slots[2] = empty_slot
        self.harness.slots[2] = empty_slot
        self.assertEqual(self.harness._audio_clip_navigation_availability(0, 1), (True, True))
        self.harness._select_adjacent_audio_clip("next")
        self.assertIs(self.harness.song_state.view.highlighted_clip_slot, empty_slot)
        self.assertEqual(self.harness.selected_clip_slot, 2)


if __name__ == "__main__":
    unittest.main()
