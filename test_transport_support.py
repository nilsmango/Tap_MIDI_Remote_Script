import ast
import pathlib
import re
import time
import unittest


SOURCE = pathlib.Path(__file__).with_name("Tap.py")


def tap_class_node():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Tap")


def extracted_method(name):
    node = next(
        node for node in tap_class_node().body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"time": time}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace[name]


class SysExHarness:
    CHUNKED_INCOMING_SYSEX_IDS = (14, 15, 16, 35, 36, 49, 50, 51, 55, 57, 58, 60, 62, 82, 88, 92, 96)
    SYSEX_CHUNK_INACTIVITY_TIMEOUT = 2.0
    SYSEX_CHUNK_MAX_ASSEMBLED_BYTES = 32
    SYSEX_CHUNK_MAX_ASSEMBLED_BYTES_BY_ID = {}
    handle_sysex = extracted_method("handle_sysex")

    def __init__(self):
        self._sysex_buffers = {}
        self.received = []
        self.logs = []

    def _handle_full_sysex(self, message):
        self.received.append(message)

    def _debug_log(self, message):
        self.logs.append(message)


class WideIndexHarness:
    extract_values_from_sysex_message = extracted_method("extract_values_from_sysex_message")
    _from_3_7bit_magnitude = extracted_method("_from_3_7bit_magnitude")
    _decode_wide_index_message = extracted_method("_decode_wide_index_message")


class NoteCodecHarness:
    NOTE_FLAG_MUTE = 0x01
    NOTE_FLAG_NEGATIVE_START = 0x02
    NOTE_FLAG_NEGATIVE_DURATION = 0x04
    NOTE_FLAG_NEGATIVE_VELOCITY_DEVIATION = 0x08
    _note_record_flags = extracted_method("_note_record_flags")


class FlinColumnHarness:
    _handle_flin_command = extracted_method("_handle_flin_command")

    def __init__(self):
        self.column = {"page": 0, "id": 3, "active": False}
        self.info = {"columns": [self.column]}
        clip = type("Clip", (), {"is_midi_clip": True})()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        self._song = type("Song", (), {"view": type("View", (), {"highlighted_clip_slot": slot})()})()
        self.saved = False

    def song(self):
        return self._song

    def _flin_info(self, _clip):
        return self.info

    def _flin_column_for_page(self, _info, page, column_index):
        return self.column if page == 0 and column_index == 3 else None

    def _save_flin_info_to_name(self, _clip, _info):
        self.saved = True

    def send_selected_clip_metadata(self):
        pass

    def _debug_log(self, message):
        raise AssertionError(message)


class TransportTests(unittest.TestCase):
    def test_flin_column_velocity_deviation_uses_the_eighth_wire_field(self):
        harness = FlinColumnHarness()
        payload = b"v1|column|0|3|101|82|4|-27"
        harness._handle_flin_command([0xF0, 0x3E, *payload, 0xF7])

        self.assertEqual(harness.column["velocity"], 101)
        self.assertEqual(harness.column["probability"], 82)
        self.assertEqual(harness.column["duration_steps"], 4)
        self.assertEqual(harness.column["velocity_deviation"], -27)
        self.assertTrue(harness.saved)

    def test_chunk_streams_are_isolated_by_manufacturer_id(self):
        harness = SysExHarness()
        harness.handle_sysex([0xF0, 14, ord("$"), 1, 2, 0xF7])
        harness.handle_sysex([0xF0, 35, ord("$"), 10, 11, 0xF7])
        harness.handle_sysex([0xF0, 14, ord("_"), 3, 0xF7])
        harness.handle_sysex([0xF0, 35, ord("_"), 12, 0xF7])

        self.assertEqual(
            harness.received,
            [
                [0xF0, 14, 1, 2, 3, 0xF7],
                [0xF0, 35, 10, 11, 12, 0xF7],
            ],
        )

    def test_single_final_chunk_is_a_complete_transfer(self):
        harness = SysExHarness()
        record = [1] * 11
        harness.handle_sysex([0xF0, 14, ord("_"), *record, 0xF7])
        self.assertEqual(harness.received, [[0xF0, 14, *record, 0xF7]])

    def test_direct_note_records_cannot_be_mistaken_for_chunk_markers(self):
        harness = SysExHarness()
        add_with_pitch_36 = [0xF0, 14, ord("$"), *([1] * 10), 0xF7]
        remove_with_id_low_byte_36 = [0xF0, 15, ord("$"), 0, 0, 0, 0, 0xF7]
        modify_with_id_low_byte_95 = [0xF0, 16, ord("_"), *([1] * 15), 0xF7]

        harness.handle_sysex(add_with_pitch_36)
        harness.handle_sysex(remove_with_id_low_byte_36)
        harness.handle_sysex(modify_with_id_low_byte_95)

        self.assertEqual(
            harness.received,
            [add_with_pitch_36, remove_with_id_low_byte_36, modify_with_id_low_byte_95],
        )
        self.assertEqual(harness._sysex_buffers, {})

    def test_note_modify_and_remove_keep_committed_chunk_framing(self):
        assignment = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "CHUNKED_INCOMING_SYSEX_IDS"
                for target in node.targets
            )
        )
        chunked_ids = ast.literal_eval(assignment.value)
        self.assertIn(15, chunked_ids)
        self.assertIn(16, chunked_ids)

    def test_direct_note_modify_reaches_live_note_by_full_id(self):
        class Note:
            note_id = 0x12345F
            pitch = 60
            start_time = 0.0
            duration = 0.25
            velocity = 70
            mute = False
            probability = 1.0
            velocity_deviation = 0

        note = Note()

        class Clip:
            start_time = 0.0
            start_marker = 0.0
            loop_start = 0.0
            loop_end = 4.0
            end_marker = 4.0
            length = 4.0

            def get_notes_extended(self, *_):
                return (note,)

            def apply_note_modifications(self, notes):
                self.applied = tuple(notes)

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        song = type("Song", (), {"view": type("View", (), {"highlighted_clip_slot": slot})()})()

        class Harness:
            CHUNKED_INCOMING_SYSEX_IDS = (14, 15, 16)
            SYSEX_CHUNK_INACTIVITY_TIMEOUT = 2.0
            SYSEX_CHUNK_MAX_ASSEMBLED_BYTES = 1024
            SYSEX_CHUNK_MAX_ASSEMBLED_BYTES_BY_ID = {}
            NOTE_FLAG_MUTE = 0x01
            NOTE_FLAG_NEGATIVE_START = 0x02
            NOTE_FLAG_NEGATIVE_DURATION = 0x04
            NOTE_FLAG_NEGATIVE_VELOCITY_DEVIATION = 0x08
            clip_length_trick = 1.0
            handle_sysex = extracted_method("handle_sysex")
            _handle_full_sysex = extracted_method("_handle_full_sysex")
            _from_5_7bit_bytes = extracted_method("_from_5_7bit_bytes")
            _from_3_7bit_magnitude = extracted_method("_from_3_7bit_magnitude")
            _value_from_magnitude = extracted_method("_value_from_magnitude")

            def song(self):
                return song

            def _debug_log(self, _message):
                pass

            def _decoupled_automation_info(self, _clip):
                return None

            def _mutator_allows_source_note_time(self, _clip, _time):
                return True

        def five_byte(value):
            return [(value >> (shift * 7)) & 0x7F for shift in range(5)]

        def magnitude(value):
            return [(value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F]

        record = (
            five_byte(note.note_id)
            + [64]
            + magnitude(500)
            + magnitude(750)
            + [111, 96, 27, 0x08]
        )
        Harness().handle_sysex([0xF0, 16, ord("_")] + record + [0xF7])

        self.assertEqual(note.pitch, 64)
        self.assertEqual(note.start_time, 0.5)
        self.assertEqual(note.duration, 0.75)
        self.assertEqual(note.velocity, 111)
        self.assertAlmostEqual(note.probability, 96 / 127.0)
        self.assertEqual(note.velocity_deviation, -27)
        self.assertEqual(clip.applied, (note,))

    def test_unrelated_non_chunked_message_does_not_cancel_active_stream(self):
        harness = SysExHarness()
        harness.handle_sysex([0xF0, 14, ord("$"), 1, 0xF7])
        harness.handle_sysex([0xF0, 99, 7, 0xF7])
        harness.handle_sysex([0xF0, 14, ord("_"), 2, 0xF7])
        self.assertEqual(harness.received[-1], [0xF0, 14, 1, 2, 0xF7])

    def test_immediate_command_clears_only_its_own_partial_stream(self):
        harness = SysExHarness()
        harness.handle_sysex([0xF0, 0x3C, ord("$"), 1, 2, 0xF7])
        harness.handle_sysex([0xF0, 0x3C, ord("Q"), 9, 0xF7])

        self.assertNotIn(0x3C, harness._sysex_buffers)
        self.assertEqual(harness.received, [[0xF0, 0x3C, ord("Q"), 9, 0xF7]])

    def test_oversized_stream_is_discarded(self):
        harness = SysExHarness()
        harness.handle_sysex([0xF0, 14, ord("$"), *([1] * 30), 0xF7])
        harness.handle_sysex([0xF0, 14, ord("$"), 2, 2, 2, 0xF7])
        harness.handle_sysex([0xF0, 14, ord("_"), 3, 0xF7])
        self.assertEqual(harness.received, [])
        self.assertTrue(any("oversized" in item for item in harness.logs))

    def test_proven_remote_chunk_limit_is_unchanged(self):
        class_node = tap_class_node()
        assignment = next(
            node for node in class_node.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "SYSEX_OUTGOING_MAX_CHUNK_LENGTH" for target in node.targets)
        )
        self.assertEqual(ast.literal_eval(assignment.value), 240)

    def test_liveness_path_no_longer_resends_project_state(self):
        method = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.FunctionDef) and node.name == "_connection_established"
        )
        calls = [
            child.func.attr
            for child in ast.walk(method)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
        ]
        # One send remains in first-time initialization. There must not be the
        # previous second resend in the already-initialized liveness branch.
        self.assertEqual(calls.count("_send_current_project_state"), 1)

    def test_wide_index_records_are_exact_and_support_more_than_127_scenes(self):
        harness = WideIndexHarness()
        message = [0xF0, 0x0A, 0, 1, 0, 1, 0, 0, 0xF7]
        decoded = harness._decode_wide_index_message(message, 0, 2)
        self.assertEqual(decoded, ([], [128, 16384]))
        self.assertIsNone(harness._decode_wide_index_message(message[:-2] + [0xF7], 0, 2))

    def test_project_snapshot_has_explicit_begin_and_end_markers(self):
        method = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.FunctionDef) and node.name == "_send_current_project_state"
        )
        literal_strings = [
            child.value for child in ast.walk(method)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        ]
        self.assertTrue(any(value.startswith("B|") for value in literal_strings))
        self.assertTrue(any(value.startswith("E|") for value in literal_strings))

    def test_velocity_deviation_has_a_dedicated_signed_flag(self):
        harness = NoteCodecHarness()
        flags = harness._note_record_flags(False, 10, 20, -64)
        self.assertEqual(flags & harness.NOTE_FLAG_NEGATIVE_VELOCITY_DEVIATION, 0x08)
        self.assertEqual(flags & harness.NOTE_FLAG_NEGATIVE_START, 0)

    def test_note_addition_reports_exact_ids_only_for_selection_transactions(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("before_ids = {", source)
        self.assertIn("added_ids = [int(note.note_id)", source)
        addition = source[source.index("# add MULTIPLE notes"):source.index("# remove note (also multiple)")]
        self.assertIn("if transaction_id is not None:", addition)
        self.assertNotIn("self.send_selected_clip_notes()", addition)

    def test_groove_mutations_are_chunk_capable(self):
        harness = SysExHarness()
        harness.handle_sysex([0xF0, 0x60, ord("$"), 1, 2, 0xF7])
        harness.handle_sysex([0xF0, 0x60, ord("_"), 3, 0xF7])
        self.assertEqual(harness.received, [[0xF0, 0x60, 1, 2, 3, 0xF7]])

    def test_scene_metadata_feature_has_no_protocol_or_per_scene_listeners(self):
        source = SOURCE.read_text(encoding="utf-8")
        for removed_name in (
            "_scene_metadata_listener_bindings",
            "_sync_scene_metadata_listeners",
            "_send_scene_metadata_snapshot",
            "_send_scene_metadata_record",
            "_handle_scene_edit",
            "_send_scene_edit_result",
        ):
            self.assertNotIn(removed_name, source)
        self.assertNotIn("message[1] == 0x5C", source)

    def test_empty_triggered_slots_use_a_distinct_non_clip_state(self):
        method = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.FunctionDef) and node.name == "_clip_slot_state_and_color"
        )
        method_source = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), method)
        self.assertIn("state = 4 if clip_slot.has_clip else 6", method_source)

    def test_dormant_groove_feature_does_not_add_project_or_topology_traffic(self):
        for method_name in ("_send_current_project_state", "_on_follow_action_topology_changed"):
            method = next(
                node for node in tap_class_node().body
                if isinstance(node, ast.FunctionDef) and node.name == method_name
            )
            calls = [
                child.func.attr
                for child in ast.walk(method)
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
            ]
            self.assertNotIn("_sync_groove_pool_listeners", calls)
            self.assertNotIn("_send_groove_pool_state", calls)

    def test_slot_delta_batch_rebuilds_each_track_cache_once(self):
        class Harness:
            _flush_clip_slot_deltas = extracted_method("_flush_clip_slot_deltas")

            def __init__(self):
                self.track = type("Track", (), {})()
                self.slots = [object(), object()]
                self.track.clip_slots = self.slots
                self._song = type("Song", (), {"tracks": [self.track]})()
                self._pending_clip_slot_deltas = {
                    (0, 0): (self.track, self.slots[0]),
                    (0, 1): (self.track, self.slots[1]),
                }
                self._clip_slot_delta_scheduled = True
                self.old_clips_array = ["old"]
                self.cache_rebuilds = 0
                self.sent = []

            def song(self):
                return self._song

            def _clip_slot_state_and_color(self, _track, _slot):
                return (1, 0)

            def _to_3_7bit_magnitude(self, value):
                return [0, 0, value]

            def _send_midi(self, message):
                self.sent.append(message)

            def _clip_slots_string_for_track(self, _track):
                self.cache_rebuilds += 1
                return "rebuilt"

        harness = Harness()
        harness._flush_clip_slot_deltas()
        self.assertEqual(len(harness.sent), 2)
        self.assertEqual(harness.cache_rebuilds, 1)
        self.assertEqual(harness.old_clips_array, ["rebuilt"])

    def test_scene_launch_does_not_scan_every_clip_slot(self):
        class IndexOnlySlots:
            def __init__(self):
                self.values = [object() for _ in range(6)]

            def __len__(self):
                return len(self.values)

            def __getitem__(self, index):
                return self.values[index]

            def __iter__(self):
                raise AssertionError("scene launch must not enumerate every slot")

        class Scene:
            def __init__(self):
                self.did_fire = False

            def fire(self):
                self.did_fire = True

        class Harness:
            _fire_scene = extracted_method("_fire_scene")

            def __init__(self):
                self.scene = Scene()
                self.track = type("Track", (), {"playing_slot_index": 2, "clip_slots": IndexOnlySlots()})()
                self._song = type("Song", (), {"scenes": [self.scene] * 6, "tracks": [self.track]})()
                self.queued = []
                self._handled_follow_action_launches = set()

            def song(self):
                return self._song

            def schedule_message(self, _delay, callback):
                callback()

            def _queue_clip_slot_delta(self, _track, scene_index, _slot):
                self.queued.append(scene_index)

            def _follow_action_key(self, *_args):
                return ("scene", 5)

            def _activate_follow_action_for_scene(self, _scene_index):
                pass

        harness = Harness()
        harness._fire_scene(5)
        self.assertTrue(harness.scene.did_fire)
        self.assertEqual(set(harness.queued), {2, 5})

    def test_ordinary_clip_add_skips_global_follow_action_rescan(self):
        class Harness:
            FOLLOW_ACTION_NAME_MARKER_RE = re.compile(r"\s*\[TapFA:v1\|([^\]]*)\]")
            _on_clip_has_clip_changed = extracted_method("_on_clip_has_clip_changed")

            def __init__(self, clip_name):
                self.track = object()
                clip = type("Clip", (), {"name": clip_name})()
                self.slot = type("Slot", (), {"has_clip": True, "clip": clip})()
                self._follow_action_rules = {}
                self.rescans = 0

            def _get_track_index(self, _track):
                return 0

            def _follow_action_key(self, *_args):
                return ("clip", 0, 0)

            def _sync_follow_action_name_listeners(self):
                self.rescans += 1

            def _load_follow_actions_from_names(self):
                self.rescans += 1

            def _sync_follow_action_runtime_listeners(self):
                self.rescans += 1

            def _refresh_parameter_metadata_on_automation_change(self):
                pass

            def _queue_clip_slot_delta(self, *_args):
                pass

            def _sync_clip_color_listeners_for_track(self, _track):
                pass

            def _set_up_notes_playing(self, _value):
                pass

        ordinary = Harness("Plain clip")
        ordinary._on_clip_has_clip_changed(ordinary.track, 0, ordinary.slot)
        self.assertEqual(ordinary.rescans, 0)

        marked = Harness("Clip [TapFA:v1|1|100|next||none|]")
        marked._on_clip_has_clip_changed(marked.track, 0, marked.slot)
        self.assertEqual(marked.rescans, 3)

    def test_playing_status_does_not_scan_slots_without_follow_rules(self):
        class NoIterationSlots:
            def __iter__(self):
                raise AssertionError("idle follow actions must not scan clip slots")

        class Harness:
            _activate_follow_actions_for_playing_clips = extracted_method("_activate_follow_actions_for_playing_clips")

            def __init__(self):
                self._follow_action_rules = {}
                track = type("Track", (), {"clip_slots": NoIterationSlots()})()
                self._song = type("Song", (), {"tracks": [track]})()

            def song(self):
                return self._song

        Harness()._activate_follow_actions_for_playing_clips()

    def test_playing_status_checks_only_clip_slots_with_follow_rules(self):
        class ForbiddenSlot:
            @property
            def has_clip(self):
                raise AssertionError("unrelated clip slot was inspected")

        class TargetSlot:
            has_clip = True
            is_playing = True

        class IndexOnlySlots:
            def __len__(self):
                return 128

            def __getitem__(self, index):
                return TargetSlot() if index == 73 else ForbiddenSlot()

            def __iter__(self):
                raise AssertionError("clip slots must not be enumerated")

        class Harness:
            _activate_follow_actions_for_playing_clips = extracted_method(
                "_activate_follow_actions_for_playing_clips"
            )

            def __init__(self):
                self._follow_action_rules = {("clip", 0, 73): {}}
                self._active_follow_actions = {}
                track = type("Track", (), {"clip_slots": IndexOnlySlots()})()
                self._song = type("Song", (), {"tracks": [track]})()
                self.activated = []

            def song(self):
                return self._song

            def _clear_finished_follow_action_launches(self):
                pass

            def _activate_follow_action_for_clip(self, track_index, scene_index, clip_slot):
                self.activated.append((track_index, scene_index, clip_slot.is_playing))

        harness = Harness()
        harness._activate_follow_actions_for_playing_clips()
        self.assertEqual(harness.activated, [(0, 73, True)])

    def test_groove_edit_has_capability_rollback_and_listener_symmetry(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("def _remove_groove_listeners", source)
        self.assertIn("self._remove_groove_listener_bindings(self._groove_pool_listener_bindings)", source)
        self.assertIn("self._remove_groove_listener_bindings(self._groove_detail_listener_bindings)", source)
        method = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.FunctionDef) and node.name == "_handle_groove_edit"
        )
        attributes = [child.attr for child in ast.walk(method) if isinstance(child, ast.Attribute)]
        self.assertIn("begin_undo_step", attributes)
        self.assertIn("end_undo_step", attributes)
        self.assertIn("_send_groove_edit_result", attributes)


if __name__ == "__main__":
    unittest.main()
