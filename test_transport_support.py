import ast
import math
import pathlib
import re
import struct
import time
import unittest


SOURCE = pathlib.Path(__file__).with_name("Tap.py")
SECRET_VERSION_NUMBER = next(
    ast.literal_eval(node.value)
    for node in ast.parse(SOURCE.read_text(encoding="utf-8")).body
    if isinstance(node, ast.Assign)
    and any(
        isinstance(target, ast.Name) and target.id == "secret_version_number"
        for target in node.targets
    )
)


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
    namespace = {
        "time": time,
        "math": math,
        "struct": struct,
        "liveobj_valid": lambda value: value is not None,
        "secret_version_number": SECRET_VERSION_NUMBER,
    }
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace[name]


class AutomationTraceSupport:
    _automation_trace_expected_group = extracted_method(
        "_automation_trace_expected_group"
    )
    _automation_trace_stored_group = extracted_method(
        "_automation_trace_stored_group"
    )

    def _automation_trace(self, transaction, stage, details=""):
        if not hasattr(self, "traces"):
            self.traces = []
        self.traces.append((str(transaction), stage, details))

    def song(self):
        return type("Song", (), {"is_playing": False})()


class SysExHarness(AutomationTraceSupport):
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


class AutomationTransferTraceHarness:
    AUTOMATION_TRACE_LOGGING_ENABLED = True
    SYSEX_STRING_ESCAPE_CHAR = "\\"
    CHUNKED_INCOMING_SYSEX_IDS = (0x32,)
    SYSEX_CHUNK_INACTIVITY_TIMEOUT = 2.0
    SYSEX_CHUNK_MAX_ASSEMBLED_BYTES = 4096
    SYSEX_CHUNK_MAX_ASSEMBLED_BYTES_BY_ID = {0x32: 4096}
    handle_sysex = extracted_method("handle_sysex")
    _automation_trace = extracted_method("_automation_trace")
    _split_escaped_sysex_fields = extracted_method("_split_escaped_sysex_fields")
    _set_automation_envelope = extracted_method("_set_automation_envelope")
    _handle_automation_diagnostic_trace = extracted_method(
        "_handle_automation_diagnostic_trace"
    )

    def __init__(self):
        self._sysex_buffers = {}
        self._automation_trace_pending_transfer = None
        self.received = []
        self.logs = []

    def _handle_full_sysex(self, message):
        self.received.append(message)

    def log_message(self, message):
        self.logs.append(message)

    def _debug_log(self, _message):
        pass


class WideIndexHarness:
    extract_values_from_sysex_message = extracted_method("extract_values_from_sysex_message")
    _from_3_7bit_magnitude = extracted_method("_from_3_7bit_magnitude")
    _decode_wide_index_message = extracted_method("_decode_wide_index_message")


class GeneratedShapeHarness:
    AUTOMATION_REPEATING_PATTERN_MAX_EXPANDED_EVENTS = 262144
    _from_3_7bit_magnitude = extracted_method("_from_3_7bit_magnitude")
    _generated_automation_uint7_le = extracted_method(
        "_generated_automation_uint7_le"
    )
    _generated_automation_double = extracted_method(
        "_generated_automation_double"
    )
    _generated_automation_wire_checksum = extracted_method(
        "_generated_automation_wire_checksum"
    )
    _generated_automation_append_node = extracted_method(
        "_generated_automation_append_node"
    )
    _generated_automation_append_cycle = extracted_method(
        "_generated_automation_append_cycle"
    )
    _generated_automation_random_value = extracted_method(
        "_generated_automation_random_value"
    )
    _generated_automation_cubic = extracted_method(
        "_generated_automation_cubic"
    )
    _generated_automation_split = extracted_method(
        "_generated_automation_split"
    )
    _generated_automation_clip_nodes = extracted_method(
        "_generated_automation_clip_nodes"
    )
    _generated_automation_nodes = extracted_method(
        "_generated_automation_nodes"
    )
    _generated_automation_compact_entry = extracted_method(
        "_generated_automation_compact_entry"
    )
    _automation_payload_checksum = extracted_method(
        "_automation_payload_checksum"
    )
    _automation_step_id = extracted_method("_automation_step_id")
    _automation_step_order = extracted_method("_automation_step_order")
    _automation_step_tuple = extracted_method("_automation_step_tuple")
    _automation_step_entry = extracted_method("_automation_step_entry")


class NoteCodecHarness:
    NOTE_FLAG_MUTE = 0x01
    NOTE_FLAG_NEGATIVE_START = 0x02
    NOTE_FLAG_NEGATIVE_DURATION = 0x04
    NOTE_FLAG_NEGATIVE_VELOCITY_DEVIATION = 0x08
    _note_record_flags = extracted_method("_note_record_flags")


class SelectedClipSnapshotHarness:
    SYSEX_OUTGOING_MAX_CHUNK_LENGTH = 240
    SELECTED_CLIP_IDENTICAL_SNAPSHOT_INTERVAL = 0.05
    send_selected_clip_notes = extracted_method("send_selected_clip_notes")

    def __init__(self):
        self.seq_status = True
        self._selected_clip_update_pending_notes = False
        self._last_selected_clip_notes_signature = None
        self._last_selected_clip_notes_sent_at = 0.0
        self.sent = []

    def _selected_clip_updates_are_suppressed(self):
        return False

    def song(self):
        view = type("View", (), {"highlighted_clip_slot": None})()
        return type("Song", (), {"view": view})()

    def _send_midi(self, message):
        self.sent.append(message)


class AutomationPencilMergeHarness:
    _automation_step_id = extracted_method("_automation_step_id")
    _automation_step_order = extracted_method("_automation_step_order")
    _automation_step_tuple = extracted_method("_automation_step_tuple")
    _automation_sort_key = extracted_method("_automation_sort_key")
    _automation_sorted_steps = extracted_method("_automation_sorted_steps")
    _merge_incremental_automation_pencil_point = extracted_method("_merge_incremental_automation_pencil_point")


class AutomationPencilWriterHarness:
    _write_incremental_automation_pencil_interval = extracted_method("_write_incremental_automation_pencil_interval")

    def __init__(self):
        self.neutralized = []
        self.logs = []

    def _decoupled_automation_info(self, _clip, _parameter):
        return None

    def _automation_envelope_supports_point_events(self, _envelope):
        return False

    def _neutralize_automation_span(self, _envelope, _parameter, start, end, value):
        self.neutralized.append((start, end, value))

    def _parameter_target_value_from_normalized(self, _parameter, value):
        return value

    def _debug_log(self, message):
        self.logs.append(message)


class NoteTransferHarness:
    clip_length_trick = 110.0
    _handle_note_transfer_command = extracted_method("_handle_note_transfer_command")
    _from_3_7bit_magnitude = extracted_method("_from_3_7bit_magnitude")
    _from_5_7bit_bytes = extracted_method("_from_5_7bit_bytes")

    def __init__(self, clip):
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        track = type("Track", (), {"clip_slots": [slot]})()
        self._song = type("Song", (), {"tracks": [track]})()
        self.results = []
        self.logs = []

    def song(self):
        return self._song

    def _mutator_allows_source_note_time(self, _clip, _time):
        return True

    def _send_note_add_result(self, transaction_id, success, error_code, note_ids):
        self.results.append((transaction_id, success, error_code, list(note_ids)))

    def _debug_log(self, message):
        self.logs.append(message)


def note_transfer_message(operation, transaction_id, destination_ms, note_ids):
    def wide(value):
        return [(value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F]

    def note_id(value):
        return [(value >> (shift * 7)) & 0x7F for shift in range(5)]

    flags = (1 if operation == "move" else 0) | (2 if destination_ms < 0 else 0)
    payload = (
        [flags]
        + wide(transaction_id)
        + wide(0)
        + wide(0)
        + wide(abs(destination_ms))
        + wide(len(note_ids))
        + [byte for value in note_ids for byte in note_id(value)]
    )
    return [0xF0, 0x5C, *payload, 0xF7]


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


class FlinTimingHarness:
    _flin_quantum_beats = extracted_method("_flin_quantum_beats")
    _flin_note_quantization_beats = extracted_method("_flin_note_quantization_beats")
    _flin_quantized_note_start = extracted_method("_flin_quantized_note_start")
    _flin_note_starts = extracted_method("_flin_note_starts")
    _flin_beats_per_bar = extracted_method("_flin_beats_per_bar")
    _flin_period_ticks_for_rows = extracted_method("_flin_period_ticks_for_rows")


class FlinProtocolHarness:
    FLIN_NAME_MARKER_RE = re.compile(r"\s*\[TapFlin:v2\|([^\]]*)\]")
    _flin_info_from_name = extracted_method("_flin_info_from_name")
    _flin_marker = extracted_method("_flin_marker")
    _flin_settings_from_payload = extracted_method("_flin_settings_from_payload")


class TransportTests(unittest.TestCase):
    def test_v54_generated_writer_batches_four_events_per_live_callback(self):
        assignment = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "AUTOMATION_EXACT_EVENT_BATCH_SIZE"
                for target in node.targets
            )
        )
        self.assertEqual(ast.literal_eval(assignment.value), 4)

    def test_v55_remote_generator_matches_swift_count_and_checksum_fixtures(self):
        harness = GeneratedShapeHarness()
        fixtures = (
            # shape, period, phase fraction, count, canonical checksum
            (0, 0.125, 0.17, 142, 0x07189B5F),
            (3, 0.5, 0.83, 38, 0x765D8021),
            (1, 0.5, 0.55, 137, 0x50DEC20B),
            (1, 0.5, 1.0, 189, 0x6B2C6522),
            (6, 1.3333333333333333, 0.5, 8, 0x13AE2848),
            (10, 0.25, 0.99, 20, 0x330C1DA6),
            (11, 0.25, 0.01, 36, 0x0EE938FF),
        )
        for shape, period, phase, expected_count, expected_checksum in fixtures:
            nodes = harness._generated_automation_nodes(
                shape, 0.0, 4.375, period, phase,
                0.07, 0.11, 23, False
            )
            canonical = ",".join(
                harness._generated_automation_compact_entry(node)
                for node in nodes
            )
            self.assertEqual(len(nodes), expected_count, shape)
            self.assertEqual(
                harness._automation_payload_checksum(canonical),
                expected_checksum,
                shape
            )

    def test_v55_terminal_group_is_always_linear(self):
        harness = GeneratedShapeHarness()
        for shape in range(12):
            nodes = harness._generated_automation_nodes(
                shape, 0.0, 4.375, 0.5, 0.37,
                0.0, 0.0, 19, False
            )
            terminal = max(node[0] for node in nodes)
            terminal_nodes = [
                node for node in nodes if abs(node[0] - terminal) <= 0.000001
            ]
            self.assertTrue(terminal_nodes, shape)
            self.assertTrue(all(
                tuple(node[2:6]) == (0.5, 0.5, 0.5, 0.5)
                for node in terminal_nodes
            ), shape)

    def test_v55_binary_command_rebuilds_and_dispatches_one_complete_shape(self):
        class Harness(GeneratedShapeHarness):
            _handle_generated_automation_shape = extracted_method(
                "_handle_generated_automation_shape"
            )

            def __init__(self):
                self.received_fields = None
                self.received_compact_response = None
                self.errors = []
                self.traces = []
                self._automation_exact_stream = None

            def _automation_trace(self, transaction, stage, details=""):
                self.traces.append((str(transaction), stage, details))

            def _resolve_automation_context(self, token, revision):
                self.assertions = (token, revision)
                return ({
                    "control_index": 6,
                    "clip": object(),
                    "device_param": object(),
                    "domain": (0.0, 4.375),
                    "point_duration": 1.0 / 16.0,
                }, None, (), revision, "ok")

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _handle_exact_automation_full_write(
                    self, fields, compact_response=False):
                self.received_fields = fields
                self.received_compact_response = compact_response

            def _finalize_automation_pencil_stroke(self):
                pass

            def _fail_exact_automation_full_write(self, _state):
                raise AssertionError("no previous write should exist")

            def _automation_write_error_response(self, *arguments, **keywords):
                self.errors.append((arguments, keywords))

        def encode_3(value):
            return [(value >> 14) & 0x7f, (value >> 7) & 0x7f, value & 0x7f]

        def encode_le(value, width):
            return [(int(value) >> (offset * 7)) & 0x7f for offset in range(width)]

        def encode_double(value):
            bits = struct.unpack(">Q", struct.pack(">d", value))[0]
            return encode_le(bits, 10)

        harness = Harness()
        payload = (
            [0x47, 1, 0]
            + encode_3(91)
            + [6, 0]
            + encode_le(0x2A, 5)
            + encode_le(0xABCDEF0123456789, 10)
            + encode_double(0.125)
            + encode_double(0.17)
            + encode_double(0.07)
            + encode_double(0.11)
            + encode_3(23)
            + encode_3(142)
            + encode_le(0x07189B5F, 5)
        )
        payload += encode_le(
            harness._generated_automation_wire_checksum(payload), 5
        )
        harness._handle_generated_automation_shape(tuple(payload))

        self.assertEqual(len(payload), 79)
        self.assertEqual(harness.errors, [])
        self.assertEqual(harness.assertions, ("0000002A", "ABCDEF0123456789"))
        self.assertIsNotNone(harness.received_fields)
        self.assertEqual(harness.received_fields[0], "F")
        self.assertEqual(harness.received_fields[1], "6")
        self.assertEqual(harness.received_fields[8], "142")
        self.assertEqual(harness.received_fields[10], "91")
        self.assertTrue(harness.received_compact_response)
        self.assertTrue(any(
            transaction == "91"
            and stage == "compact_shape_valid"
            and "writer=direct_rtl" in details
            for transaction, stage, details in harness.traces
        ))

        # Dropping Ball owns this field as Bounce, where the upper endpoint is
        # a real value. Periodic shapes still reserve 1.0 as wrapped phase 0.
        ball_payload = (
            [0x47, 1, 0]
            + encode_3(92)
            + [6, 1]
            + encode_le(0x2A, 5)
            + encode_le(0xABCDEF0123456789, 10)
            + encode_double(0.5)
            + encode_double(1.0)
            + encode_double(0.07)
            + encode_double(0.11)
            + encode_3(23)
            + encode_3(189)
            + encode_le(0x6B2C6522, 5)
        )
        ball_payload += encode_le(
            harness._generated_automation_wire_checksum(ball_payload), 5
        )
        harness._handle_generated_automation_shape(tuple(ball_payload))

        self.assertEqual(harness.errors, [])
        self.assertEqual(harness.received_fields[8], "189")
        self.assertEqual(harness.received_fields[10], "92")

    def test_flin_rate_curves_never_duplicate_and_ignore_note_quantization(self):
        harness = FlinTimingHarness()
        clip = type("Clip", (), {"signature_numerator": 4, "signature_denominator": 4})()

        for base_quarters in (1, 2, 4, 8, 12, 16, 32, 64):
            for mode in range(4):
                baseline = None
                for quantization in range(6):
                    periods = harness._flin_period_ticks_for_rows({
                        "base_quarters": base_quarters,
                        "rate_mode": mode,
                        "quantization": quantization,
                    }, clip)
                    self.assertEqual(len(set(periods)), 16)
                    self.assertTrue(all(left < right for left, right in zip(periods, periods[1:])))
                    if baseline is None:
                        baseline = periods
                    self.assertEqual(periods, baseline)

        self.assertEqual(
            harness._flin_period_ticks_for_rows({"base_quarters": 16, "rate_mode": 0}, clip),
            tuple(range(16, 257, 16)),
        )

    def test_flin_note_quantization_snaps_only_onsets_and_wraps_loop_end(self):
        harness = FlinTimingHarness()
        self.assertEqual(harness._flin_quantized_note_start({"quantization": 0}, 0.1875, 4.0), 0.1875)
        self.assertEqual(harness._flin_quantized_note_start({"quantization": 2}, 0.1875, 4.0), 0.25)
        self.assertEqual(harness._flin_quantized_note_start({"quantization": 4}, 3.75, 4.0), 0.0)

    def test_flin_quantization_defaults_to_first_placement_only(self):
        harness = FlinTimingHarness()
        first_only = harness._flin_note_starts(
            {"quantization": 2}, phase_ticks=1, period_ticks=3, loop_ticks=16
        )
        quantize_all = harness._flin_note_starts(
            {"quantization": 2, "quantize_all": True},
            phase_ticks=1,
            period_ticks=3,
            loop_ticks=16,
        )

        self.assertEqual(first_only, (0.0, 0.1875, 0.375, 0.5625, 0.75, 0.9375))
        self.assertEqual(quantize_all, (0.0, 0.25, 0.5, 0.75))

    def test_flin_v2_protocol_requires_quantize_all_and_rejects_legacy_shapes(self):
        harness = FlinProtocolHarness()
        marker = harness._flin_marker({
            "kind": 0,
            "quantization": 2,
            "quantize_all": True,
            "base_quarters": 8,
            "rate_mode": 1,
            "horizon_bars": 32,
            "mapping_mode": 0,
            "global_offset": 0,
            "view_page": 0,
            "base_pitch": 60,
            "seed": 7,
            "default_velocity": 100,
            "limited": False,
            "columns": [],
        })
        parsed = harness._flin_info_from_name(marker)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed["quantize_all"])
        self.assertIsNone(harness._flin_info_from_name(marker.replace("|a=1|", "|a=2|")))
        self.assertIsNone(harness._flin_info_from_name(marker.replace("TapFlin:v2", "TapFlin:v1")))

        columns = ",".join(
            "{}:0:0:1:0:{}:0:{}:100:100:0".format(index, index, index)
            for index in range(16)
        )
        payload = [
            "v2", "settings", "0", "2", "0", "8", "1", "32", "0",
            "0", "0", "60", "7", "100", columns,
        ]
        self.assertFalse(harness._flin_settings_from_payload(payload)["quantize_all"])
        malformed_boolean = list(payload)
        malformed_boolean[4] = "2"
        self.assertIsNone(harness._flin_settings_from_payload(malformed_boolean))
        self.assertIsNone(harness._flin_settings_from_payload(payload[:-1]))

    def test_identical_selected_clip_snapshot_is_only_suppressed_briefly(self):
        harness = SelectedClipSnapshotHarness()

        harness.send_selected_clip_notes()
        harness.send_selected_clip_notes()
        self.assertEqual(len(harness.sent), 1)

        harness._last_selected_clip_notes_sent_at -= 1.0
        harness.send_selected_clip_notes()
        self.assertEqual(len(harness.sent), 2)

    def test_incremental_pencil_seeds_authored_layer_from_live_once(self):
        parameter = object()
        envelope = object()

        class Clip:
            def automation_envelope(self, requested_parameter):
                self.requested_parameter = requested_parameter
                return envelope

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()

        class Harness:
            _begin_automation_pencil_stroke = extracted_method(
                "_begin_automation_pencil_stroke"
            )

            def _finalize_automation_pencil_stroke(self):
                self._automation_pencil_stroke = None

            def song(self):
                view = type("View", (), {"highlighted_clip_slot": slot})()
                return type("Song", (), {"view": view})()

            def _current_connected_parameter_for_control(self, _control_index):
                return parameter

            def _parameter_is_automatable(self, _parameter):
                return True

            def _parameter_automation_is_enabled(self, _parameter):
                return True

            def _authored_automation_steps(self, _clip, _parameter, _control_index):
                return None

            def _automation_steps_from_envelope_events(self, *args):
                self.event_args = args
                return None

            def _automation_steps_from_envelope_samples(self, *args):
                self.sample_args = args
                return ((0.0, 0.125, 0.4, 0.0, 0, 0),)

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

        harness = Harness()
        harness._begin_automation_pencil_stroke(
            7,
            ["P", "B", "7", "3", "0.0", "4.0", "0.125", "0.03125"]
        )

        state = harness._automation_pencil_stroke
        self.assertTrue(state["had_authored_steps"])
        self.assertEqual(state["logical_steps"], ((0.0, 0.125, 0.4, 0.0, 0, 0),))
        self.assertEqual(harness.event_args[2:], (0.0, 4.0, 0.125))
        self.assertEqual(harness.sample_args[2:], (0.0, 4.0, 0.125))

    def test_exact_live_event_read_does_not_invent_baseline_points(self):
        class Envelope:
            def events_in_range(self, start, end):
                self.range = (start, end)
                return ()

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _parameter_normalized_value(self, _parameter):
                return 0.5

            def _debug_log(self, message):
                raise AssertionError(message)

        parameter = type("Parameter", (), {"min": -48.0, "max": 48.0})()
        envelope = Envelope()
        steps = Harness()._automation_steps_from_envelope_events(
            envelope, parameter, 1.0, 3.0, 0.03125
        )

        self.assertEqual(steps, ())
        self.assertEqual(envelope.range, (1.0, 4.0000001))

    def test_exact_live_event_read_preserves_all_four_curve_coefficients(self):
        controls = type("Controls", (), {
            "x1": 0.12,
            "y1": 0.34,
            "x2": 0.78,
            "y2": 0.91,
        })()
        event = type("Event", (), {
            "time": 1.25,
            "value": 9.6,
            "control_coefficients": controls,
        })()

        class Envelope:
            def events_in_range(self, _start, _end):
                return (event,)

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _parameter_normalized_value(self, _parameter):
                return 0.5

            def _debug_log(self, message):
                raise AssertionError(message)

        parameter = type("Parameter", (), {"min": -48.0, "max": 48.0})()
        steps = Harness()._automation_steps_from_envelope_events(
            Envelope(), parameter, 0.0, 4.0, 0.03125
        )
        self.assertEqual(
            steps,
            ((1.25, 0.03125, 0.6, 0.0, 0, 1, True, 0.12, 0.34, 0.78, 0.91),)
        )

    def test_exact_device_event_values_use_envelope_parameter_domain_without_losing_points(self):
        controls = type("Controls", (), {
            "x1": 0.1,
            "y1": 0.2,
            "x2": 0.7,
            "y2": 0.9,
        })()
        events = (
            type("Event", (), {
                "time": 1.0,
                "value": 632.5,
                "control_coefficients": controls,
            })(),
            type("Event", (), {
                "time": 2.0,
                "value": 10010.0,
                "control_coefficients": controls,
            })(),
        )

        class Envelope:
            def __init__(self):
                self.sampled_times = []

            def events_in_range(self, _start, _end):
                return events

            def value_at_time(self, time_value):
                self.sampled_times.append(time_value)
                return {1.0: 0.25, 2.0: 0.75}[time_value]

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        envelope = Envelope()
        steps = Harness()._automation_steps_from_envelope_events(
            envelope,
            type("Parameter", (), {"min": 0.0, "max": 1.0})(),
            0.0,
            4.0,
            0.03125
        )

        self.assertEqual([step[2] for step in steps], [0.25, 0.75])
        self.assertEqual(envelope.sampled_times, [1.0, 2.0])
        self.assertEqual(steps[0][7:], (0.1, 0.2, 0.7, 0.9))

    def test_exact_nonlinear_volume_events_use_live_envelope_conversion(self):
        controls = type("Controls", (), {
            "x1": 0.14,
            "y1": 0.28,
            "x2": 0.72,
            "y2": 0.86,
        })()
        events = tuple(
            type("Event", (), {
                "time": time_value,
                "value": value,
                "control_coefficients": controls,
            })()
            for time_value, value in ((1.0, 0.01), (2.0, 1.0))
        )

        class Envelope:
            def __init__(self):
                self.sampled_times = []

            def events_in_range(self, _start, _end):
                return events

            def value_at_time(self, time_value):
                self.sampled_times.append(time_value)
                # Live converts the stored gain to its fader/control domain.
                return {1.0: 0.25, 2.0: 0.85}[time_value]

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        envelope = Envelope()
        parameter = type("Parameter", (), {
            "min": 0.0,
            "max": 1.0,
            "value": 1.0,
        })()
        steps = Harness()._automation_steps_from_envelope_events(
            envelope, parameter, 0.0, 4.0, 0.03125
        )

        self.assertEqual([step[2] for step in steps], [0.25, 0.85])
        self.assertEqual(envelope.sampled_times, [1.0, 2.0])
        self.assertEqual(steps[0][7:], (0.14, 0.28, 0.72, 0.86))

    def test_transformed_same_time_events_keep_both_sides_of_vertical_boundary(self):
        controls = type("Controls", (), {
            "x1": 0.5,
            "y1": 0.5,
            "x2": 0.5,
            "y2": 0.5,
        })()
        events = tuple(
            type("Event", (), {
                "time": 1.0,
                "value": value,
                "control_coefficients": controls,
            })()
            for value in (20.0, 20000.0)
        )

        class Envelope:
            def events_in_range(self, _start, _end):
                return events

            def value_at_time(self, time_value):
                return 0.2 if time_value < 1.0 else 0.8

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        steps = Harness()._automation_steps_from_envelope_events(
            Envelope(),
            type("Parameter", (), {"min": 0.0, "max": 1.0})(),
            0.0,
            4.0,
            0.03125
        )

        self.assertEqual([step[2] for step in steps], [0.2, 0.8])
        self.assertEqual([step[0] for step in steps], [1.0, 1.0])

    def test_same_time_event_sampling_preserves_negative_domains(self):
        controls = type("Controls", (), {
            "x1": 0.5,
            "y1": 0.5,
            "x2": 0.5,
            "y2": 0.5,
        })()
        events = tuple(
            type("Event", (), {
                "time": -1.0,
                "value": value,
                "control_coefficients": controls,
            })()
            for value in (0.2, 0.8)
        )

        class Envelope:
            def __init__(self):
                self.sampled_times = []

            def events_in_range(self, _start, _end):
                return events

            def value_at_time(self, time_value):
                self.sampled_times.append(time_value)
                return 0.2 if time_value < -1.0 else 0.8

        class Harness:
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        envelope = Envelope()
        steps = Harness()._automation_steps_from_envelope_events(
            envelope,
            type("Parameter", (), {"min": 0.0, "max": 1.0})(),
            -2.0,
            4.0,
            0.03125
        )

        self.assertEqual([step[2] for step in steps], [0.2, 0.8])
        self.assertLess(envelope.sampled_times[0], 0.0)

    def test_same_time_event_order_preserves_lives_returned_vertical_direction(self):
        low_controls = type("Controls", (), {
            "x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4,
        })()
        high_controls = type("Controls", (), {
            "x1": 0.9, "y1": 0.8, "x2": 0.7, "y2": 0.6,
        })()
        low_event = type("Event", (), {
            "time": 1.0, "value": 0.2, "control_coefficients": low_controls,
        })()
        high_event = type("Event", (), {
            "time": 1.0, "value": 0.8, "control_coefficients": high_controls,
        })()

        class Envelope:
            def __init__(self, before, after, events):
                self.before = before
                self.after = after
                self.events = events
                self.value_calls = []

            def events_in_range(self, _start, _end):
                return self.events

            def value_at_time(self, time_value):
                self.value_calls.append(time_value)
                return self.before if time_value < 1.0 else self.after

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _ordered_same_time_automation_events = extracted_method(
                "_ordered_same_time_automation_events"
            )
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        parameter = type("Parameter", (), {"min": 0.0, "max": 1.0})()
        rising_envelope = Envelope(0.2, 0.8, (low_event, high_event))
        rising = Harness()._automation_steps_from_envelope_events(
            rising_envelope,
            parameter, 0.0, 2.0, 0.03125
        )
        self.assertEqual([step[2] for step in rising], [0.2, 0.8])
        self.assertEqual([step[7] for step in rising], [0.1, 0.9])
        self.assertEqual(len(rising_envelope.value_calls), 2)

        falling_envelope = Envelope(0.8, 0.2, (high_event, low_event))
        falling = Harness()._automation_steps_from_envelope_events(
            falling_envelope,
            parameter, 0.0, 2.0, 0.03125
        )
        for actual, expected in zip((step[2] for step in falling), (0.8, 0.2)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual([step[7] for step in falling], [0.9, 0.1])
        self.assertEqual(len(falling_envelope.value_calls), 2)

    def test_same_time_order_and_outgoing_coefficients_survive_a_misleading_post_sample(self):
        low_controls = type("Controls", (), {
            "x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4,
        })()
        outgoing_controls = type("Controls", (), {
            "x1": 0.0, "y1": 1.0, "x2": 0.0, "y2": 1.0,
        })()
        low_event = type("Event", (), {
            "time": 1.0, "value": 0.2, "control_coefficients": low_controls,
        })()
        high_event = type("Event", (), {
            "time": 1.0, "value": 0.8, "control_coefficients": outgoing_controls,
        })()

        class Envelope:
            def __init__(self):
                self.sampled_times = []

            def events_in_range(self, _start, _end):
                return (low_event, high_event)

            def value_at_time(self, time_value):
                self.sampled_times.append(time_value)
                if time_value < 1.0:
                    return 0.2
                # The outgoing leading-corner curve has already reached the
                # following low point just after the boundary. Event order and
                # coefficients remain authoritative, while a prior raw-value
                # match restores the known vertical sides.
                return 0.1

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _ordered_same_time_automation_events = extracted_method(
                "_ordered_same_time_automation_events"
            )
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )
            _automation_steps_preserving_unchanged_vertical_values = extracted_method(
                "_automation_steps_preserving_unchanged_vertical_values"
            )
            _automation_step_tuple = extracted_method("_automation_step_tuple")
            _automation_step_id = extracted_method("_automation_step_id")
            _automation_step_order = extracted_method("_automation_step_order")

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _debug_log(self, message):
                raise AssertionError(message)

        envelope = Envelope()
        harness = Harness()
        sampled_steps = harness._automation_steps_from_envelope_events(
            envelope,
            type("Parameter", (), {"min": 0.0, "max": 1.0})(),
            0.0,
            2.0,
            0.03125
        )
        current_records = (
            (1.0, 0.2, 0.1, 0.2, 0.3, 0.4),
            (1.0, 0.8, 0.0, 1.0, 0.0, 1.0),
        )
        previous_steps = (
            tuple(list(sampled_steps[0][:2]) + [0.2] + list(sampled_steps[0][3:])),
            tuple(list(sampled_steps[1][:2]) + [0.8] + list(sampled_steps[1][3:])),
        )
        previous_records = (
            (1.0, 0.2, 0.1, 0.2, 0.3, 0.4),
            (1.0, 0.8, 0.5, 0.5, 0.5, 0.5),
        )
        steps = harness._automation_steps_preserving_unchanged_vertical_values(
            sampled_steps,
            current_records,
            previous_steps,
            previous_records
        )

        self.assertEqual([step[2] for step in steps], [0.2, 0.8])
        self.assertEqual([step[7] for step in steps], [0.1, 0.0])
        self.assertEqual(len(envelope.sampled_times), 2)
        self.assertTrue(any(time_value > 1.0 for time_value in envelope.sampled_times))

        changed_records = (
            current_records[0],
            (1.0, 0.7, 0.0, 1.0, 0.0, 1.0),
        )
        changed = harness._automation_steps_preserving_unchanged_vertical_values(
            sampled_steps,
            changed_records,
            previous_steps,
            previous_records
        )
        self.assertEqual([step[2] for step in changed], [0.2, 0.1])

    def test_exact_event_writer_creates_right_to_left_so_live_retains_outgoing_curves(self):
        class Envelope:
            def __init__(self):
                self.deleted = []

            def delete_events_in_range(self, start, end):
                self.deleted.append((start, end))

        class Harness:
            _write_exact_automation_events_to_envelope = extracted_method(
                "_write_exact_automation_events_to_envelope"
            )

            def __init__(self):
                self.created = []

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_steps_use_exact_events(self, _steps):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: step[0]))

            def _parameter_target_value_from_normalized(self, parameter, value):
                return parameter.min + ((parameter.max - parameter.min) * value)

            def _create_automation_event(self, _envelope, time_value, raw_value, step):
                self.created.append((time_value, raw_value, step[4]))

            def _debug_log(self, message):
                raise AssertionError(message)

        steps = (
            (1.0, 0.1, 0.2, 0.0, 1, 1, True, 0.2, 0.8, 0.7, 0.9),
            (1.0, 0.1, 0.4, 0.0, 3, 2, True, 0.5, 0.5, 0.5, 0.5),
            (2.0, 0.1, 0.8, 0.0, 2, 2, True, 0.5, 0.5, 0.5, 0.5),
        )
        envelope = Envelope()
        harness = Harness()
        self.assertTrue(
            harness._write_exact_automation_events_to_envelope(
                envelope,
                type("Parameter", (), {"min": -48.0, "max": 48.0})(),
                0.0,
                4.0,
                steps
            )
        )
        self.assertEqual(
            [(time_value, step_id) for time_value, _raw_value, step_id in harness.created],
            [(2.0, 2), (1.0, 1), (1.0, 3)]
        )
        for (_, actual, _), expected in zip(harness.created, (28.8, -28.8, -9.6)):
            self.assertAlmostEqual(actual, expected)

    def test_exact_event_writer_corrects_a_live_runtime_that_prepends_same_time_events(self):
        class Envelope:
            def __init__(self):
                self.events = []
                self.deletes = []
                self.read_count = 0

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [event for event in self.events if not start <= event.time <= end]

            def events_in_range(self, start, end):
                self.read_count += 1
                return tuple(event for event in self.events if start <= event.time <= end)

        class Harness:
            _write_exact_automation_events_to_envelope = extracted_method(
                "_write_exact_automation_events_to_envelope"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_steps_use_exact_events(self, _steps):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: (step[0], step[5])))

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, envelope, time_value, raw_value, step):
                # Simulate a Live binding that prepends equal-time creations.
                envelope.events.insert(0, type("Event", (), {
                    "time": time_value,
                    "value": raw_value,
                    "order": step[5],
                })())

            def _debug_log(self, message):
                raise AssertionError(message)

        for first_value, second_value in ((0.2, 0.8), (0.8, 0.2)):
            steps = (
                (1.0, 0.1, first_value, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
                (1.0, 0.1, second_value, 0.0, 2, 2, True, 0.5, 0.5, 0.5, 0.5),
            )
            envelope = Envelope()
            self.assertTrue(
                Harness()._write_exact_automation_events_to_envelope(
                    envelope,
                    type("Parameter", (), {"min": 0.0, "max": 1.0})(),
                    0.0,
                    2.0,
                    steps
                )
            )
            self.assertEqual(
                [event.value for event in envelope.events],
                [first_value, second_value]
            )
            self.assertEqual(len(envelope.deletes), 2)
            self.assertEqual(envelope.read_count, 2)

    def test_new_device_envelope_defers_full_write_like_the_first_pencil_point(self):
        envelope = object()

        class Clip:
            def __init__(self, mutations):
                self.mutations = mutations

            def create_automation_envelope(self, _parameter):
                self.mutations.append("create_envelope")
                return envelope

        class Harness:
            AUTOMATION_EXACT_NEW_ENVELOPE_SETTLE_TICKS = 2
            _handle_exact_automation_full_write = extracted_method(
                "_handle_exact_automation_full_write"
            )
            _exact_automation_time_groups = extracted_method(
                "_exact_automation_time_groups"
            )

            def __init__(self):
                self.scheduled = []
                self.performed = 0
                self.errors = []
                self.mutations = []
                self._automation_exact_stream = None
                self.parameter = object()
                self.context = {
                    "clip": Clip(self.mutations),
                    "device_param": self.parameter,
                    "control_index": 0,
                    "domain": (0.0, 4.0),
                }

            def _begin_undo_step(self):
                self.mutations.append("begin_undo")
                return True

            def _end_undo_step(self, _started):
                self.mutations.append("end_undo")

            def _fail_exact_automation_full_write(self, _state):
                raise AssertionError("no previous write should exist")

            def _automation_payload_checksum(self, _payload):
                return 0

            def _resolve_automation_context(self, _token, _revision):
                return self.context, None, (), "REV", "ok"

            def _automation_step_from_entry(self, _entry, domain=None, fallback_order=0):
                return (0.0, 0.1, 0.25, 0.0, 1, fallback_order, True, 0.5, 0.5, 0.5, 0.5)

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: (step[0], step[5])))

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _parameter_automation_is_enabled(self, _parameter):
                return False

            def _automation_envelope_supports_point_events(self, candidate):
                return candidate is envelope

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_exact_automation_full_write(self, _state):
                self.performed += 1

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

        fields = [
            "F", "0", "CTX", "REV", "0", "4", "0.1",
            "entry", "1", "00000000", "9",
        ]
        harness = Harness()
        harness._handle_exact_automation_full_write(fields)

        self.assertEqual(harness.performed, 0)
        self.assertEqual(len(harness.scheduled), 1)
        self.assertEqual(harness.scheduled[0][0], 2)
        self.assertEqual(harness.errors, [])
        self.assertEqual(harness.mutations, ["begin_undo", "create_envelope"])
        self.assertTrue(harness._automation_exact_stream["undo_step_started"])
        harness.scheduled[0][1]()
        self.assertEqual(harness.performed, 1)

    def test_exact_shape_is_validated_before_scheduled_points_and_curves_use_one_undo(self):
        class Envelope:
            def __init__(self):
                self.events = []
                self.deletes = []

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [
                    event for event in self.events
                    if not start <= event.time <= end
                ]

            def events_in_range(self, start, end):
                return tuple(
                    event for event in self.events
                    if start <= event.time <= end
                )

        class Clip:
            def __init__(self, target_envelope):
                self.target_envelope = target_envelope
                self.create_calls = 0

            def create_automation_envelope(self, _parameter):
                self.create_calls += 1
                return self.target_envelope

        class Harness(AutomationTraceSupport):
            AUTOMATION_REPEATING_PATTERN_MAX_EXPANDED_EVENTS = 262144
            AUTOMATION_EXACT_NEW_ENVELOPE_SETTLE_TICKS = 2
            AUTOMATION_EXACT_POST_COMMIT_SETTLE_TICKS = 2
            AUTOMATION_EXACT_STREAM_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _handle_exact_automation_stream = extracted_method(
                "_handle_exact_automation_stream"
            )
            _automation_step_from_compact_stream_entry = extracted_method(
                "_automation_step_from_compact_stream_entry"
            )
            _automation_group_has_non_linear_controls = extracted_method(
                "_automation_group_has_non_linear_controls"
            )
            _linear_exact_automation_group = extracted_method(
                "_linear_exact_automation_group"
            )
            _perform_streamed_exact_automation_step = extracted_method(
                "_perform_streamed_exact_automation_step"
            )
            _delete_streamed_exact_automation_group = extracted_method(
                "_delete_streamed_exact_automation_group"
            )
            _streamed_exact_automation_range_is_empty = extracted_method(
                "_streamed_exact_automation_range_is_empty"
            )
            _verify_streamed_exact_automation_clear = extracted_method(
                "_verify_streamed_exact_automation_clear"
            )
            _verify_streamed_exact_automation_step = extracted_method(
                "_verify_streamed_exact_automation_step"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )
            _close_exact_automation_write_attempt = extracted_method(
                "_close_exact_automation_write_attempt"
            )

            def __init__(self):
                self._automation_exact_stream = None
                self._automation_trace_pending_transfer = None
                self.begin_calls = 0
                self.end_calls = 0
                self.scheduled = []
                self.errors = []
                self.failed = False
                self.reenable_calls = 0

            def _resolve_automation_context(self, _token, _revision):
                return ({
                    "control_index": 2,
                    "clip": clip,
                    "device_param": object(),
                    "domain": (0.0, 2.0),
                }, None, (), "REV", "ok")

            def _finalize_automation_pencil_stroke(self):
                pass

            def _parameter_automation_is_enabled(self, _parameter):
                return False

            def _re_enable_parameter_automation(self, _parameter):
                self.reenable_calls += 1

            def _automation_envelope_supports_point_events(self, candidate):
                return candidate is envelope

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _refresh_exact_automation_write_envelope(self, state, allow_create=False):
                return state["envelope"]

            def _begin_undo_step(self):
                self.begin_calls += 1
                return True

            def _end_undo_step(self, started):
                if started:
                    self.end_calls += 1

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, target, time_value, raw_value, step):
                controls = type("Controls", (), {
                    "x1": step[7], "y1": step[8],
                    "x2": step[9], "y2": step[10],
                })()
                event = type("Event", (), {
                    "time": time_value,
                    "value": raw_value,
                    "coefficients": step[7:11],
                    "control_coefficients": controls,
                })()
                # Live prepends at an occupied timestamp. Its handler creates
                # vertical groups in reverse so their settled order matches
                # the authored pair on the first pass.
                insertion_index = next((
                    index for index, existing in enumerate(target.events)
                    if abs(existing.time - time_value) <= 0.000001
                ), len(target.events))
                target.events.insert(insertion_index, event)
                target.events.sort(key=lambda candidate: candidate.time)

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: (step[0], step[5])))

            def _automation_payload_checksum(self, value):
                checksum = 2166136261
                for byte in value.encode("utf-8"):
                    checksum ^= byte
                    checksum = (checksum * 16777619) & 0xFFFFFFFF
                return checksum

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _verify_exact_automation_full_write(self, _state):
                pass

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

            def _debug_log(self, _message):
                pass

        left = "0.000000:0.500000:0.333333333:0.523598776:0.666666667:1.000000000"
        vertical_low = "1.000000:0.000000"
        vertical_high = "1.000000:1.000000"
        right = "2.000000:0.500000:0.250000000:0.250000000:0.750000000:0.750000000"
        wire_entries = ",".join((left, vertical_low, vertical_high, right))
        envelope = Envelope()
        clip = Clip(envelope)
        harness = Harness()
        header = [
            "S", "12", "2", "CTX", "REV", "0", "2", "0.01",
            "4", "3", "2",
        ]
        checksum = harness._automation_payload_checksum(
            "|".join(header + [wire_entries])
        )
        corrupted = Harness()
        corrupted._handle_exact_automation_stream(
            header + ["{:08X}".format(checksum ^ 1), wire_entries]
        )
        self.assertEqual(corrupted.scheduled, [])
        self.assertTrue(corrupted.errors)
        self.assertEqual(envelope.deletes, [])
        self.assertEqual(envelope.events, [])

        harness._handle_exact_automation_stream(
            header + ["{:08X}".format(checksum), wire_entries]
        )
        self.assertEqual(harness.begin_calls, 0)
        self.assertEqual(envelope.deletes, [])
        self.assertEqual(envelope.events, [])
        self.assertEqual(clip.create_calls, 1)
        self.assertEqual(len(harness.scheduled), 1)
        self.assertEqual(harness.scheduled[0][0], 2)

        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.begin_calls, 1)
        self.assertEqual(len(envelope.deletes), 1)
        self.assertEqual(envelope.events, [])

        # The full-range clear gets its own settled read and an empty callback
        # before the first point can be created.
        harness.scheduled.pop(0)[1]()
        self.assertEqual(envelope.events, [])
        harness.scheduled.pop(0)[1]()
        self.assertEqual([event.time for event in envelope.events], [0.0])
        self.assertEqual(envelope.events[0].coefficients, (0.5, 0.5, 0.5, 0.5))

        # A successful read-back only schedules the following mutation.
        harness.scheduled.pop(0)[1]()
        self.assertEqual([event.time for event in envelope.events], [0.0])
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.begin_calls, 1)
        self.assertEqual(
            [(event.time, event.value) for event in envelope.events],
            [(0.0, 0.5), (1.0, 0.0), (1.0, 1.0)],
        )

        harness.scheduled.pop(0)[1]()
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.begin_calls, 1)
        self.assertEqual([event.time for event in envelope.events], [0.0, 1.0, 1.0, 2.0])
        self.assertTrue(all(
            event.coefficients == (0.5, 0.5, 0.5, 0.5)
            for event in envelope.events
        ))

        # The final point read switches phase, then a separate callback begins
        # the right-to-left curved replacements.
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness._automation_exact_stream["stream_phase"], "curves")
        harness.scheduled.pop(0)[1]()
        right_event = next(event for event in envelope.events if event.time == 2.0)
        self.assertEqual(
            right_event.coefficients,
            (0.25, 0.25, 0.75, 0.75),
        )

        harness.scheduled.pop(0)[1]()
        harness.scheduled.pop(0)[1]()
        left_event = next(event for event in envelope.events if event.time == 0.0)
        self.assertEqual(left_event.coefficients, (
            0.333333333, 0.523598776, 0.666666667, 1.0,
        ))
        self.assertEqual(
            [(event.time, event.value) for event in envelope.events if event.time == 1.0],
            [(1.0, 0.0), (1.0, 1.0)],
        )

        harness.scheduled.pop(0)[1]()
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.reenable_calls, 1)
        self.assertEqual(harness.end_calls, 1)
        self.assertEqual(len(harness.scheduled), 1)
        self.assertEqual(harness.scheduled[0][0], 2)
        self.assertFalse(harness.failed)
        self.assertEqual(harness.errors, [])
        trace_stages = [stage for _transaction, stage, _details in harness.traces]
        self.assertIn("payload_valid", trace_stages)
        self.assertIn("clear_write", trace_stages)
        self.assertIn("clear_read", trace_stages)
        self.assertIn("point_write", trace_stages)
        self.assertIn("point_read", trace_stages)
        self.assertIn("curve_write", trace_stages)
        self.assertIn("curve_read", trace_stages)

    def test_malformed_exact_shape_cancels_an_active_write_without_mutating(self):
        class Harness(AutomationTraceSupport):
            _handle_exact_automation_stream = extracted_method(
                "_handle_exact_automation_stream"
            )

            def __init__(self):
                self._automation_exact_stream = {"stream_id": "12"}
                self.failed = []
                self.pencil_finalized = 0

            def _finalize_automation_pencil_stroke(self):
                self.pencil_finalized += 1

            def _fail_exact_automation_full_write(self, state):
                self.failed.append(state)

        harness = Harness()
        harness._handle_exact_automation_stream(["S", "X", "12"])
        self.assertEqual(harness.failed, [harness._automation_exact_stream])
        self.assertEqual(harness.pencil_finalized, 1)
        self.assertEqual(harness.traces[-1][1], "payload_reject")

    def test_streamed_shape_waits_and_rewrites_a_wrong_device_value_before_advancing(self):
        class Parameter:
            min = 20.0
            max = 120.0

        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        class Event:
            def __init__(self, time_value, value):
                self.time = time_value
                self.value = value
                self.control_coefficients = Controls()

        class Envelope:
            def __init__(self):
                self.events = [Event(0.5, 20.0)]
                self.deletes = []

            def events_in_range(self, start, end):
                return tuple(
                    event for event in self.events
                    if start <= event.time <= end
                )

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [
                    event for event in self.events
                    if not start <= event.time <= end
                ]

        class Harness(AutomationTraceSupport):
            AUTOMATION_EXACT_STREAM_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _verify_streamed_exact_automation_step = extracted_method(
                "_verify_streamed_exact_automation_step"
            )
            _delete_streamed_exact_automation_group = extracted_method(
                "_delete_streamed_exact_automation_group"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

            def __init__(self):
                self._automation_exact_stream = None
                self.scheduled = []
                self.failed = False

            def _refresh_exact_automation_write_envelope(self, state, allow_create=False):
                return state["envelope"]

            def _parameter_target_value_from_normalized(self, parameter, normalized):
                return parameter.min + ((parameter.max - parameter.min) * normalized)

            def _create_automation_event(self, envelope, time_value, raw_value, step):
                envelope.events.append(Event(time_value, raw_value))

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_streamed_exact_automation_step(self, _state):
                pass

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

        group = ((
            0.5, 0.1, 0.75, 0.0, 1, 1, True,
            0.5, 0.5, 0.5, 0.5,
        ),)
        envelope = Envelope()
        state = {
            "stream_id": "12",
            "context": {"device_param": Parameter()},
            "envelope": envelope,
            "write_start": 0.0,
            "write_end": 1.0,
            "time_groups": (group,),
            "pending_group": group,
            "pending_phase": "points",
            "pending_group_index": 0,
            "pending_settle_polls": 0,
            "pending_write_attempts": 1,
            "point_group_index": 0,
            "curve_group_index": 0,
            "stream_phase": "points",
            "group_creation_reversed": {},
            "completed": False,
        }
        harness = Harness()
        harness._automation_exact_stream = state

        harness._verify_streamed_exact_automation_step(state)
        self.assertEqual(state["point_group_index"], 0)
        self.assertEqual(state["pending_settle_polls"], 1)
        self.assertEqual(envelope.deletes, [])
        harness.scheduled.pop(0)[1]()
        self.assertEqual(state["pending_settle_polls"], 2)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(state["pending_write_attempts"], 2)
        self.assertEqual(len(envelope.deletes), 1)
        self.assertEqual([event.value for event in envelope.events], [95.0])
        self.assertEqual(state["point_group_index"], 0)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(state["point_group_index"], 1)
        self.assertIsNone(state["pending_group"])
        self.assertFalse(harness.failed)

    def test_streamed_square_reverses_creation_only_after_stored_order_disagrees(self):
        class Parameter:
            min = 20.0
            max = 120.0

        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        class Event:
            def __init__(self, value):
                self.time = 0.5
                self.value = value
                self.control_coefficients = Controls()

        class Envelope:
            def __init__(self):
                self.events = [Event(110.0), Event(30.0)]

            def events_in_range(self, start, end):
                return tuple(
                    event for event in self.events
                    if start <= event.time <= end
                )

            def delete_events_in_range(self, start, end):
                self.events = [
                    event for event in self.events
                    if not start <= event.time <= end
                ]

        class Harness(AutomationTraceSupport):
            AUTOMATION_EXACT_STREAM_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _verify_streamed_exact_automation_step = extracted_method(
                "_verify_streamed_exact_automation_step"
            )
            _delete_streamed_exact_automation_group = extracted_method(
                "_delete_streamed_exact_automation_group"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

            def __init__(self):
                self._automation_exact_stream = None
                self.scheduled = []
                self.failed = False

            def _refresh_exact_automation_write_envelope(self, state, allow_create=False):
                return state["envelope"]

            def _parameter_target_value_from_normalized(self, parameter, normalized):
                return parameter.min + ((parameter.max - parameter.min) * normalized)

            def _create_automation_event(self, envelope, _time, raw_value, _step):
                # Model the Live binding that exposes equal-time events in the
                # opposite order from their create_event calls.
                envelope.events.insert(0, Event(raw_value))

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_streamed_exact_automation_step(self, _state):
                pass

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

        group = (
            (0.5, 0.1, 0.1, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
            (0.5, 0.1, 0.9, 0.0, 2, 2, True, 0.5, 0.5, 0.5, 0.5),
        )
        state = {
            "stream_id": "13",
            "context": {"device_param": Parameter()},
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 1.0,
            "time_groups": (group,),
            "pending_group": group,
            "pending_phase": "points",
            "pending_group_index": 0,
            "pending_settle_polls": 2,
            "pending_write_attempts": 1,
            "point_group_index": 0,
            "curve_group_index": 0,
            "stream_phase": "points",
            "group_creation_reversed": {},
            "completed": False,
        }
        harness = Harness()
        harness._automation_exact_stream = state

        harness._verify_streamed_exact_automation_step(state)
        self.assertTrue(state["group_creation_reversed"][0.5])
        self.assertEqual([event.value for event in state["envelope"].events], [30.0, 110.0])
        self.assertEqual(state["point_group_index"], 0)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(state["point_group_index"], 1)
        self.assertFalse(harness.failed)

    def test_streamed_shape_retries_a_full_clear_that_live_did_not_accept(self):
        class Event:
            time = 0.5

        class Envelope:
            def __init__(self):
                self.events = [Event()]
                self.delete_calls = 1

            def events_in_range(self, start, end):
                return tuple(
                    event for event in self.events
                    if start <= event.time <= end
                )

            def delete_events_in_range(self, _start, _end):
                self.delete_calls += 1
                self.events = []

        class Harness(AutomationTraceSupport):
            AUTOMATION_EXACT_STREAM_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _streamed_exact_automation_range_is_empty = extracted_method(
                "_streamed_exact_automation_range_is_empty"
            )
            _verify_streamed_exact_automation_clear = extracted_method(
                "_verify_streamed_exact_automation_clear"
            )

            def __init__(self):
                self._automation_exact_stream = None
                self.scheduled = []
                self.failed = False
                self.performed = False

            def _refresh_exact_automation_write_envelope(self, state, allow_create=False):
                return state["envelope"]

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_streamed_exact_automation_step(self, _state):
                self.performed = True

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

        state = {
            "stream_id": "14",
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 1.0,
            "clear_settle_polls": 2,
            "clear_write_attempts": 1,
            "completed": False,
        }
        harness = Harness()
        harness._automation_exact_stream = state

        harness._verify_streamed_exact_automation_clear(state)
        self.assertEqual(state["clear_write_attempts"], 2)
        self.assertEqual(state["envelope"].delete_calls, 2)
        self.assertFalse(harness.performed)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(len(harness.scheduled), 1)
        harness.scheduled.pop(0)[1]()
        self.assertTrue(harness.performed)
        self.assertFalse(harness.failed)

    def test_full_write_spreads_descending_event_groups_across_live_ticks(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        class Envelope:
            def __init__(self):
                self.events = []
                self.deletes = []

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [event for event in self.events if not start <= event.time <= end]

            def events_in_range(self, start, end):
                return tuple(event for event in self.events if start <= event.time <= end)

        class Harness:
            AUTOMATION_EXACT_EVENT_BATCH_SIZE = 1
            AUTOMATION_EXACT_EVENT_BATCH_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_POST_COMMIT_SETTLE_TICKS = 2
            _perform_exact_automation_full_write = extracted_method(
                "_perform_exact_automation_full_write"
            )
            _verify_exact_automation_full_batch = extracted_method(
                "_verify_exact_automation_full_batch"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )
            _close_exact_automation_write_attempt = extracted_method(
                "_close_exact_automation_write_attempt"
            )

            def __init__(self):
                self.scheduled = []
                self.failed = False
                self.begin_calls = 0
                self.end_calls = 0
                self.audit_calls = 0

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _begin_undo_step(self):
                self.begin_calls += 1
                return True

            def _end_undo_step(self, started):
                if started:
                    self.end_calls += 1

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, envelope, time_value, raw_value, step):
                controls = type("Controls", (), {
                    "x1": step[7], "y1": step[8], "x2": step[9], "y2": step[10],
                })()
                envelope.events.append(type("Event", (), {
                    "time": time_value,
                    "value": raw_value,
                    "control_coefficients": controls,
                })())

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

            def _verify_exact_automation_full_write(self, _state):
                self.audit_calls += 1

        steps = tuple(
            (time_value, 0.1, value, 0.0, index, index, True, 0.5, 0.5, 0.5, 0.5)
            for index, (time_value, value) in enumerate(((2.0, 0.8), (1.0, 0.4), (0.0, 0.2)), 1)
        )
        envelope = Envelope()
        state = {
            "context": {"clip": object(), "device_param": object()},
            "envelope": envelope,
            "write_start": 0.0,
            "write_end": 2.0,
            "time_groups": tuple((step,) for step in steps),
            "next_group_index": 0,
            "active_batch": (),
            "batch_settle_polls": 0,
            "group_creation_reversed": {},
            "cleared": False,
            "undo_step_started": False,
            "completed": False,
        }
        harness = Harness()
        harness._perform_exact_automation_full_write(state)

        self.assertEqual([event.time for event in envelope.events], [2.0])
        self.assertEqual(len(envelope.deletes), 1)
        self.assertEqual(harness.begin_calls, 1)
        self.assertEqual(len(harness.scheduled), 1)
        harness.scheduled.pop(0)[1]()
        self.assertEqual([event.time for event in envelope.events], [2.0, 1.0])
        self.assertEqual(len(harness.scheduled), 1)
        harness.scheduled.pop(0)[1]()
        self.assertEqual([event.time for event in envelope.events], [2.0, 1.0, 0.0])
        self.assertFalse(harness.failed)

        # Finish the last batch. The attempt must close before its final audit
        # is scheduled, so commit-time coefficient loss cannot remain hidden.
        self.assertEqual(harness.end_calls, 0)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.end_calls, 1)
        self.assertEqual(harness.audit_calls, 0)
        self.assertEqual(len(harness.scheduled), 1)
        self.assertEqual(harness.scheduled[0][0], 2)
        harness.scheduled.pop(0)[1]()
        self.assertEqual(harness.audit_calls, 1)

        # A structural settled-read replay starts a fresh committed attempt.
        state["cleared"] = False
        state["next_group_index"] = 0
        state["awaiting_final_audit"] = False
        harness.scheduled = []
        harness._perform_exact_automation_full_write(state)
        self.assertEqual(harness.begin_calls, 2)

    def test_delta_writer_clears_only_its_disjoint_affected_intervals(self):
        class Event:
            def __init__(self, time_value):
                self.time = time_value

        class Envelope:
            def __init__(self):
                self.events = [Event(value) for value in (0.0, 1.0, 2.0, 3.0)]
                self.deletes = []

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [
                    event for event in self.events
                    if not start <= event.time <= end
                ]

        class Harness:
            AUTOMATION_EXACT_EVENT_BATCH_SIZE = 1
            AUTOMATION_EXACT_POST_COMMIT_SETTLE_TICKS = 2
            _perform_exact_automation_full_write = extracted_method(
                "_perform_exact_automation_full_write"
            )
            _close_exact_automation_write_attempt = extracted_method(
                "_close_exact_automation_write_attempt"
            )

            def __init__(self):
                self.scheduled = []

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _verify_exact_automation_full_write(self, _state):
                pass

            def _fail_exact_automation_full_write(self, _state):
                raise AssertionError("write should not fail")

            def _debug_log(self, message):
                raise AssertionError(message)

        envelope = Envelope()
        state = {
            "context": {"clip": object(), "device_param": object()},
            "envelope": envelope,
            "write_start": 0.9,
            "write_end": 3.1,
            "write_intervals": ((0.9, 1.1), (2.9, 3.1)),
            "time_groups": (),
            "next_group_index": 0,
            "active_batch": (),
            "batch_settle_polls": 0,
            "group_creation_reversed": {},
            "cleared": False,
            "undo_step_started": False,
            "automation_should_re_enable": False,
            "completed": False,
        }

        Harness()._perform_exact_automation_full_write(state)

        self.assertEqual([event.time for event in envelope.events], [0.0, 2.0])
        self.assertEqual(len(envelope.deletes), 2)
        self.assertEqual(envelope.deletes[0][0], 0.9)
        self.assertEqual(envelope.deletes[1][0], 2.9)

    def test_phase_endpoint_and_following_vertical_use_separate_callbacks(self):
        class Envelope:
            def __init__(self):
                self.events = []

            def delete_events_in_range(self, _start, _end):
                self.events = []

        class Harness:
            AUTOMATION_EXACT_EVENT_BATCH_SIZE = 4
            AUTOMATION_EXACT_POST_COMMIT_SETTLE_TICKS = 2
            _perform_exact_automation_full_write = extracted_method(
                "_perform_exact_automation_full_write"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )

            def __init__(self):
                self.scheduled = []

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _begin_undo_step(self):
                return True

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, envelope, time_value, raw_value, step):
                envelope.events.append((time_value, raw_value, step[7:11]))

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _fail_exact_automation_full_write(self, _state):
                raise AssertionError("write should not fail")

            def _debug_log(self, message):
                raise AssertionError(message)

        endpoint = (
            4.0, 0.1, 0.4, 0.0, 1, 1, True,
            0.5, 0.5, 0.5, 0.5,
        )
        vertical = (
            (3.494201, 0.1, 0.2, 0.0, 2, 2, True,
             0.5, 0.5, 0.5, 0.5),
            (3.494201, 0.1, 1.0, 0.0, 3, 3, True,
             0.163161, 0.480139, 0.494914, 0.810190),
        )
        state = {
            "context": {"clip": object(), "device_param": object()},
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 4.0,
            "time_groups": ((endpoint,), vertical),
            "next_group_index": 0,
            "active_batch": (),
            "batch_settle_polls": 0,
            "group_creation_reversed": {},
            "cleared": False,
            "undo_step_started": False,
            "completed": False,
        }
        harness = Harness()
        harness._perform_exact_automation_full_write(state)

        self.assertEqual([event[0] for event in state["envelope"].events], [4.0])
        self.assertEqual(state["active_batch"], ((endpoint,),))
        self.assertEqual(state["next_group_index"], 1)
        self.assertEqual(len(harness.scheduled), 1)

    def test_equal_time_batch_settles_each_timestamp_inside_one_undo(self):
        class Envelope:
            def __init__(self):
                self.events = []
                self.deletes = []

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))
                self.events = [
                    event for event in self.events
                    if not start <= event.time <= end
                ]

            def events_in_range(self, start, end):
                return tuple(event for event in self.events if start <= event.time <= end)

        class Harness:
            AUTOMATION_EXACT_EVENT_BATCH_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _verify_exact_automation_full_batch = extracted_method(
                "_verify_exact_automation_full_batch"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )
            _create_exact_automation_group = extracted_method(
                "_create_exact_automation_group"
            )
            _delete_streamed_exact_automation_group = extracted_method(
                "_delete_streamed_exact_automation_group"
            )

            def __init__(self, prepend):
                self.prepend = prepend
                self.scheduled = []
                self.failed = False
                self.performed = False
                self.traces = []

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, envelope, time_value, raw_value, step):
                controls = type("Controls", (), {
                    "x1": step[7], "y1": step[8],
                    "x2": step[9], "y2": step[10],
                })()
                event = type("Event", (), {
                    # Device envelopes can retain a sub-microbeat offset. The
                    # retry deletion must still remove this exact event group.
                    "time": time_value + (0.0000005 if not self.prepend else 0.0),
                    "value": raw_value,
                    "control_coefficients": controls,
                })()
                if self.prepend:
                    envelope.events.insert(0, event)
                else:
                    envelope.events.append(event)

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_exact_automation_full_write(self, _state):
                self.performed = True

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

            def _automation_trace(self, transaction, stage, details=""):
                self.traces.append((transaction, stage, details))

        ramp_groups = (
            (
                "up",
                (
                    (0.0, 0.1, 1.0, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
                    (0.0, 0.1, 0.0, 0.0, 2, 2, True, 0.55, 0.0, 0.88, 0.32),
                ),
            ),
            (
                "down",
                (
                    (0.0, 0.1, 0.0, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
                    (0.0, 0.1, 1.0, 0.0, 2, 2, True, 0.12, 0.68, 0.45, 1.0),
                ),
            ),
        )
        for label, group in ramp_groups:
            for prepend in (True, False):
                with self.subTest(ramp=label, prepend=prepend):
                    probe_group = tuple(
                        tuple([1.0] + list(step[1:])) for step in group
                    )
                    envelope = Envelope()
                    state = {
                        "stream_id": "ramp",
                        "context": {"device_param": object()},
                        "envelope": envelope,
                        "write_start": 0.0,
                        "write_end": 1.0,
                        # The rightmost edge is probed first. The learned
                        # direction must also be applied to the next edge.
                        "time_groups": (probe_group, group),
                        "active_batch": (probe_group,),
                        "batch_settle_polls": 0,
                        "batch_write_attempts": 1,
                        "group_creation_reversed": {},
                        "next_group_index": 1,
                        "cleared": True,
                        "undo_step_attempted": True,
                        "undo_step_started": True,
                        "completed": False,
                    }
                    harness = Harness(prepend)
                    harness._create_exact_automation_group(state, probe_group)
                    harness._verify_exact_automation_full_batch(state)

                    if prepend:
                        self.assertEqual(envelope.deletes, [])
                        self.assertTrue(state["group_creation_reversed"][1.0])
                    else:
                        # Appending envelopes reject the initial reversed probe;
                        # retry exactly this batch without closing the undo step.
                        self.assertEqual(len(envelope.deletes), 1)
                        self.assertFalse(state["group_creation_reversed"][1.0])
                        self.assertTrue(state["undo_step_started"])
                        self.assertEqual(len(harness.scheduled), 1)
                        harness.scheduled.pop(0)[1]()

                    # A later timestamp is not forced to use this edge's
                    # direction; Live may choose differently for that edge.
                    self.assertNotIn(0.0, state["group_creation_reversed"])

                    self.assertEqual(
                        [event.value for event in envelope.events],
                        [probe_group[0][2], probe_group[1][2]],
                    )
                    self.assertEqual(
                        tuple(
                            getattr(envelope.events[1].control_coefficients, name)
                            for name in ("x1", "y1", "x2", "y2")
                        ),
                        probe_group[1][7:11],
                    )
                    self.assertTrue(harness.performed)
                    self.assertFalse(harness.failed)

    def test_final_committed_mismatch_fails_without_a_second_undo_write(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        class Event:
            def __init__(self, time_value, value):
                self.time = time_value
                self.value = value
                self.control_coefficients = Controls()

        class Envelope:
            def __init__(self):
                # Internal creation order initially matches the authored pair.
                self.events = [Event(1.0, 1.0), Event(1.0, 0.0)]
                self.deletes = []

            def events_in_range(self, start, end):
                selected = [event for event in self.events if start <= event.time <= end]
                # Simulate the Live behavior observed in practice: the later
                # full-range enumeration exposes an equal-time pair opposite
                # to its earlier narrow read.
                return tuple(reversed(selected))

            def delete_events_in_range(self, start, end):
                self.deletes.append((start, end))

        class Harness:
            AUTOMATION_EXACT_MAX_FULL_REPLAYS = 3
            AUTOMATION_EXACT_POST_COMMIT_SETTLE_TICKS = 2
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _exact_automation_final_event_status = extracted_method(
                "_exact_automation_final_event_status"
            )
            _retry_exact_automation_full_write = extracted_method(
                "_retry_exact_automation_full_write"
            )
            _close_exact_automation_write_attempt = extracted_method(
                "_close_exact_automation_write_attempt"
            )
            def __init__(self):
                self.scheduled = []
                self.failed = False
                self.performed = False
                self.traces = []

            def _end_undo_step(self, _started):
                pass

            def _re_enable_parameter_automation(self, _parameter):
                pass

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _perform_exact_automation_full_write(self, _state):
                self.performed = True

            def _debug_log(self, _message):
                pass

            def _automation_trace(self, transaction, stage, details=""):
                self.traces.append((transaction, stage, details))

        group = (
            (1.0, 0.1, 1.0, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
            (1.0, 0.1, 0.0, 0.0, 2, 2, True, 0.5, 0.5, 0.5, 0.5),
        )
        state = {
            "context": {"device_param": object()},
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 2.0,
            "time_groups": (group,),
            "full_replays": 0,
            "batch_settle_polls": 0,
            "group_creation_reversed": {},
            "next_group_index": 1,
            "active_batch": (),
            "cleared": True,
            "awaiting_final_audit": True,
            "undo_step_started": False,
            "allow_full_replay": False,
            "completed": False,
        }
        harness = Harness()

        status = harness._exact_automation_final_event_status(state)
        self.assertFalse(status["exact"])
        self.assertEqual(status["reason"], "order")
        self.assertEqual(status["reversed_times"], (1.0,))

        original_events = tuple(state["envelope"].events)
        harness._retry_exact_automation_full_write(state, status)
        self.assertEqual(harness.scheduled, [])
        self.assertEqual(tuple(state["envelope"].events), original_events)
        self.assertEqual(state["envelope"].deletes, [])
        self.assertTrue(harness.failed)
        self.assertFalse(harness.performed)

    def test_final_audit_does_not_sample_values_beside_vertical_ramps(self):
        class Controls:
            x1 = 0.163161
            y1 = 0.480139
            x2 = 0.494914
            y2 = 0.810190

        class Event:
            def __init__(self, value):
                self.time = 1.25
                self.value = value
                self.control_coefficients = Controls()

        class Envelope:
            def events_in_range(self, start, end):
                return (Event(20.0), Event(5000.0)) if start <= 1.25 <= end else ()

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _exact_automation_final_event_status = extracted_method(
                "_exact_automation_final_event_status"
            )

            def _parameter_domain_values_from_envelope_events(self, *_arguments):
                raise AssertionError("vertical values must not be sampled")

        controls = (Controls.x1, Controls.y1, Controls.x2, Controls.y2)
        group = (
            (1.25, 0.1, 0.0, 0.0, 1, 1, True) + controls,
            (1.25, 0.1, 1.0, 0.0, 2, 2, True) + controls,
        )
        parameter = type("Parameter", (), {"min": 0.0, "max": 1.0})()
        status = Harness()._exact_automation_final_event_status({
            "context": {"device_param": parameter},
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 2.0,
            "time_groups": (group,),
        })

        self.assertTrue(status["exact"])
        self.assertEqual(status["reason"], "ok")

    def test_persistently_dropped_batch_fails_without_committed_replay(self):
        class Harness:
            AUTOMATION_EXACT_EVENT_BATCH_MAX_SETTLE_POLLS = 2
            AUTOMATION_EXACT_STREAM_MAX_GROUP_ATTEMPTS = 3
            _verify_exact_automation_full_batch = extracted_method(
                "_verify_exact_automation_full_batch"
            )

            def __init__(self):
                self.scheduled = []
                self.performed = False
                self.failed = False

            def _exact_automation_group_status(self, _envelope, _group, *_bounds):
                return "count"

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _perform_exact_automation_full_write(self, _state):
                self.performed = True

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

        group = (
            (1.0, 0.1, 0.5, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
        )
        state = {
            "envelope": object(),
            "write_start": 0.0,
            "write_end": 2.0,
            "active_batch": (group,),
            "batch_settle_polls": 2,
            "batch_write_attempts": 3,
            "full_replays": 0,
            "group_creation_reversed": {},
            "context": {"device_param": object()},
            "next_group_index": 1,
            "cleared": True,
            "completed": False,
        }
        harness = Harness()
        harness._verify_exact_automation_full_batch(state)

        self.assertEqual(state["full_replays"], 0)
        self.assertEqual(state["next_group_index"], 1)
        self.assertTrue(state["cleared"])
        self.assertEqual(harness.scheduled, [])
        self.assertTrue(harness.failed)
        self.assertFalse(harness.performed)

    def test_final_committed_audit_detects_lost_first_sine_bezier(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        event = type("Event", (), {
            "time": 0.0,
            "value": 0.5,
            "control_coefficients": Controls(),
        })()

        class Envelope:
            def events_in_range(self, start, end):
                return (event,) if start <= event.time <= end else ()

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _exact_automation_final_event_status = extracted_method(
                "_exact_automation_final_event_status"
            )

        sine_out = (
            0.0, 0.0625, 0.5, 0.0, 1, 1, True,
            1.0 / 3.0, math.pi / 6.0, 2.0 / 3.0, 1.0,
        )
        status = Harness()._exact_automation_final_event_status({
            "envelope": Envelope(),
            "write_start": 0.0,
            "write_end": 1.0,
            "time_groups": ((sine_out,),),
        })

        self.assertFalse(status["exact"])
        self.assertEqual(status["reason"], "coefficients")
        self.assertEqual(status["mismatch_groups"], ((sine_out,),))

    def test_delta_final_audit_reads_the_whole_envelope_not_only_patch_ranges(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        class Event:
            def __init__(self, time_value):
                self.time = time_value
                self.value = 0.5
                self.control_coefficients = Controls()

        class Envelope:
            def __init__(self):
                self.queries = []
                self.events = tuple(Event(value) for value in (0.0, 1.0, 2.0))

            def events_in_range(self, start, end):
                self.queries.append((start, end))
                return tuple(
                    event for event in self.events
                    if start <= event.time <= end
                )

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _exact_automation_final_event_status = extracted_method(
                "_exact_automation_final_event_status"
            )

        steps = tuple(
            (time_value, 0.125, 0.5, 0.0, index, index, True,
             0.5, 0.5, 0.5, 0.5)
            for index, time_value in enumerate((0.0, 1.0, 2.0), start=1)
        )
        envelope = Envelope()
        status = Harness()._exact_automation_final_event_status({
            "envelope": envelope,
            "write_start": 0.0,
            "write_end": 2.0,
            "write_intervals": ((0.99999, 1.00001),),
            "time_groups": ((steps[1],),),
            "audit_time_groups": tuple((step,) for step in reversed(steps)),
        })

        self.assertTrue(status["exact"])
        self.assertEqual(envelope.queries, [(0.0, 2.0000001)])

    def test_first_sine_batch_read_never_queries_a_negative_beat(self):
        class Controls:
            def __init__(self, values):
                self.x1, self.y1, self.x2, self.y2 = values

        class Event:
            def __init__(self, time_value, value, controls):
                self.time = time_value
                self.value = value
                self.control_coefficients = Controls(controls)

        class Envelope:
            def __init__(self):
                self.events = []
                self.queries = []

            def events_in_range(self, start, end):
                self.queries.append((start, end))
                return tuple(event for event in self.events if start <= event.time <= end)

        class Harness:
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

        sine_out = (
            0.0, 0.0625, 0.5, 0.0, 1, 1, True,
            1.0 / 3.0, math.pi / 6.0, 2.0 / 3.0, 1.0,
        )
        envelope = Envelope()
        envelope.events.append(Event(0.0, 0.5, sine_out[7:11]))
        status = Harness()._exact_automation_group_status(
            envelope, (sine_out,), write_start=0.0, write_end=4.0
        )

        self.assertEqual(status, "ok")
        self.assertEqual(len(envelope.queries), 1)
        self.assertEqual(envelope.queries[0][0], 0.0)
        self.assertGreater(envelope.queries[0][1], 0.0)

    def test_device_event_verification_uses_parameter_domain_readback(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        event = type("Event", (), {
            "time": 0.5,
            # Live can expose this in a display/event domain for devices.
            "value": 244.948975,
            "control_coefficients": Controls(),
        })()

        class Envelope:
            def events_in_range(self, start, end):
                return (event,) if start <= event.time <= end else ()

            def value_at_time(self, _time):
                return 0.5

        class Harness:
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

            def _parameter_target_value_from_normalized(self, parameter, normalized):
                return parameter.min + ((parameter.max - parameter.min) * normalized)

        parameter = type("Parameter", (), {"min": 0.0, "max": 1.0})()
        step = (
            0.5, 0.0625, 0.5, 0.0, 1, 1, True,
            0.5, 0.5, 0.5, 0.5,
        )
        status = Harness()._exact_automation_group_status(
            Envelope(), (step,), write_start=0.0, write_end=1.0,
            device_param=parameter
        )

        self.assertEqual(status, "ok")

    def test_direct_writer_does_not_sample_values_before_neighbors_exist(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        event = type("Event", (), {
            "time": 0.5,
            # A device event can expose its display-domain value here.
            "value": 244.948975,
            "control_coefficients": Controls(),
        })()

        class Envelope:
            def events_in_range(self, start, end):
                return (event,) if start <= event.time <= end else ()

            def value_at_time(self, _time):
                # Until the left neighbor exists, Live reports a transient
                # value which must not reject an otherwise stored event.
                return 0.0

        class Harness:
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

            def _parameter_target_value_from_normalized(self, parameter, normalized):
                return parameter.min + ((parameter.max - parameter.min) * normalized)

        parameter = type("Parameter", (), {"min": 0.0, "max": 1.0})()
        step = (
            0.5, 0.0625, 0.5, 0.0, 1, 1, True,
            0.5, 0.5, 0.5, 0.5,
        )
        harness = Harness()

        self.assertEqual(
            harness._exact_automation_group_status(
                Envelope(), (step,), 0.0, 1.0, parameter, False
            ),
            "ok"
        )
        self.assertEqual(
            harness._exact_automation_group_status(
                Envelope(), (step,), 0.0, 1.0, parameter, True
            ),
            "value"
        )

    def test_phase_point_verification_accepts_live_time_rounding(self):
        class Controls:
            x1 = y1 = x2 = y2 = 0.5

        intended_time = 3.494201
        event = type("Event", (), {
            "time": intended_time + 0.000005,
            "value": 0.4,
            "control_coefficients": Controls(),
        })()

        class Envelope:
            def events_in_range(self, start, end):
                return (event,) if start <= event.time <= end else ()

        class Harness:
            AUTOMATION_EXACT_EVENT_TIME_TOLERANCE = 0.00001
            _exact_automation_group_status = extracted_method(
                "_exact_automation_group_status"
            )

        step = (
            intended_time, 0.0625, 0.4, 0.0, 1, 1, True,
            0.5, 0.5, 0.5, 0.5,
        )
        status = Harness()._exact_automation_group_status(
            Envelope(), (step,), 0.0, 4.0, None, False
        )

        self.assertEqual(status, "ok")

    def test_final_full_range_audit_never_acknowledges_exhausted_mismatch(self):
        class Harness:
            AUTOMATION_EXACT_MAX_FULL_REPLAYS = 3
            _retry_exact_automation_full_write = extracted_method(
                "_retry_exact_automation_full_write"
            )

            def __init__(self):
                self.failed = False

            def _fail_exact_automation_full_write(self, _state):
                self.failed = True

            def _debug_log(self, _message):
                pass

        state = {"full_replays": 3, "completed": False}
        harness = Harness()
        harness._retry_exact_automation_full_write(
            state,
            {
                "exact": False,
                "structural": True,
                "mismatch_groups": (),
                "reversed_times": (),
                "reason": "missing",
            }
        )

        self.assertTrue(harness.failed)

    def test_incremental_pencil_points_share_one_idempotently_closed_undo_step(self):
        class Harness:
            _append_automation_pencil_point = extracted_method(
                "_append_automation_pencil_point"
            )
            _finalize_automation_pencil_stroke = extracted_method(
                "_finalize_automation_pencil_stroke"
            )
            _fail_automation_pencil_stroke = extracted_method(
                "_fail_automation_pencil_stroke"
            )

            def __init__(self):
                self.begin_count = 0
                self.end_count = 0
                self.writes = []
                self._automation_pencil_stroke = {
                    "stroke_id": 7,
                    "control_index": 2,
                    "clip": object(),
                    "device_param": object(),
                    "loop_start": 0.0,
                    "loop_end": 4.0,
                    "point_duration": 0.125,
                    "logical_steps": (),
                    "had_authored_steps": False,
                    "last_point": None,
                    "next_sequence": 1,
                    "entries": [],
                    "failed": False,
                    "undo_step_attempted": False,
                    "undo_step_started": False,
                    "last_activity": time.monotonic(),
                }

            def _begin_undo_step(self):
                self.begin_count += 1
                return True

            def _end_undo_step(self, started):
                if started:
                    self.end_count += 1

            def _write_incremental_automation_pencil_interval(self, _state, previous, point):
                self.writes.append((previous, point))
                return True

            def _merge_incremental_automation_pencil_point(self, steps, _previous, point):
                return tuple(steps) + (point,)

            def _store_authored_automation_steps(self, *_args):
                pass

            def _automation_write_error_response(self, *_args, **_kwargs):
                raise AssertionError("unexpected pencil failure")

        harness = Harness()
        harness._append_automation_pencil_point(7, ["P", "P", "7", "1:1.000000:0.250000:11:1"])
        harness._append_automation_pencil_point(7, ["P", "P", "7", "2:1.125000:0.750000:12:2"])
        self.assertEqual(harness.begin_count, 1)
        self.assertEqual(len(harness.writes), 2)

        state = harness._automation_pencil_stroke
        harness._finalize_automation_pencil_stroke(state)
        harness._finalize_automation_pencil_stroke(state)
        self.assertEqual(harness.end_count, 1)

    def test_malformed_first_pencil_point_never_opens_an_undo_step(self):
        class Harness:
            _append_automation_pencil_point = extracted_method(
                "_append_automation_pencil_point"
            )
            _finalize_automation_pencil_stroke = extracted_method(
                "_finalize_automation_pencil_stroke"
            )
            _fail_automation_pencil_stroke = extracted_method(
                "_fail_automation_pencil_stroke"
            )

            def __init__(self):
                self.begin_count = 0
                self.end_count = 0
                self.errors = 0
                self._automation_pencil_stroke = {
                    "stroke_id": 8,
                    "control_index": 0,
                    "failed": False,
                    "undo_step_attempted": False,
                    "undo_step_started": False,
                }

            def _begin_undo_step(self):
                self.begin_count += 1
                return True

            def _end_undo_step(self, _started):
                self.end_count += 1

            def _automation_write_error_response(self, *_args, **_kwargs):
                self.errors += 1

        harness = Harness()
        harness._append_automation_pencil_point(8, ["P", "P", "8", "malformed"])
        self.assertEqual(harness.begin_count, 0)
        self.assertEqual(harness.end_count, 0)
        self.assertEqual(harness.errors, 1)
        self.assertIsNone(harness._automation_pencil_stroke)

    def test_pencil_timeout_closes_an_open_group_once(self):
        class Harness:
            AUTOMATION_PENCIL_INACTIVITY_TIMEOUT = 8.0
            _expire_automation_pencil_stroke = extracted_method(
                "_expire_automation_pencil_stroke"
            )
            _finalize_automation_pencil_stroke = extracted_method(
                "_finalize_automation_pencil_stroke"
            )

            def __init__(self):
                self.end_count = 0
                self._automation_pencil_stroke = {
                    "undo_step_started": True,
                    "last_activity": 10.0,
                }

            def _end_undo_step(self, started):
                if started:
                    self.end_count += 1

        harness = Harness()
        harness._expire_automation_pencil_stroke(now=19.0)
        harness._expire_automation_pencil_stroke(now=20.0)
        self.assertEqual(harness.end_count, 1)

    def test_malformed_active_pencil_packet_closes_the_open_group(self):
        class Harness:
            _append_automation_pencil_point = extracted_method(
                "_append_automation_pencil_point"
            )
            _finalize_automation_pencil_stroke = extracted_method(
                "_finalize_automation_pencil_stroke"
            )
            _fail_automation_pencil_stroke = extracted_method(
                "_fail_automation_pencil_stroke"
            )

            def __init__(self):
                self.end_count = 0
                self.error_count = 0
                self._automation_pencil_stroke = {
                    "stroke_id": 9,
                    "control_index": 1,
                    "failed": False,
                    "undo_step_started": True,
                }

            def _end_undo_step(self, started):
                if started:
                    self.end_count += 1

            def _automation_write_error_response(self, *_args, **_kwargs):
                self.error_count += 1

        harness = Harness()
        harness._append_automation_pencil_point(9, ["P", "P", "9"])
        self.assertEqual(harness.error_count, 1)
        self.assertEqual(harness.end_count, 1)
        self.assertIsNone(harness._automation_pencil_stroke)

    def test_empty_pencil_stroke_finalizes_without_an_undo_group(self):
        class Harness:
            _finalize_automation_pencil_stroke = extracted_method(
                "_finalize_automation_pencil_stroke"
            )

            def __init__(self):
                self.end_count = 0
                self._automation_pencil_stroke = {
                    "undo_step_started": False,
                }

            def _end_undo_step(self, _started):
                self.end_count += 1

        harness = Harness()
        harness._finalize_automation_pencil_stroke()
        self.assertEqual(harness.end_count, 0)
        self.assertIsNone(harness._automation_pencil_stroke)

    def test_exact_delta_reconstructs_the_changed_event_and_local_neighbourhood(self):
        class Harness:
            _automation_step_id = extracted_method("_automation_step_id")
            _automation_step_order = extracted_method("_automation_step_order")
            _automation_step_tuple = extracted_method("_automation_step_tuple")
            _automation_sort_key = extracted_method("_automation_sort_key")
            _automation_sorted_steps = extracted_method("_automation_sorted_steps")
            _automation_step_from_entry = extracted_method("_automation_step_from_entry")
            _reconstruct_exact_automation_delta = extracted_method(
                "_reconstruct_exact_automation_delta"
            )

        baseline = tuple(
            (float(index), 0.125, index / 100.0, 0.0, 0, index + 1, True, 0.5, 0.5, 0.5, 0.5)
            for index in range(100)
        )
        replacement = "50.000000:0.125000:0.900000:0.000000:55:51:1:0.200000000:0.800000000:0.700000000:0.900000000"
        reconstructed = Harness()._reconstruct_exact_automation_delta(
            baseline,
            ["R:50:50:" + replacement],
            (0.0, 99.0)
        )
        self.assertIsNotNone(reconstructed)
        final_steps, intervals = reconstructed
        self.assertEqual(len(final_steps), 100)
        self.assertEqual(final_steps[50][2], 0.9)
        self.assertEqual(intervals, ((49.0, 51.0),))
        self.assertEqual(final_steps[0][7:], baseline[0][7:])
        self.assertEqual(final_steps[99][7:], baseline[99][7:])

    def test_exact_delta_extends_left_only_across_curves_live_can_reset(self):
        class Harness:
            _automation_step_id = extracted_method("_automation_step_id")
            _automation_step_order = extracted_method("_automation_step_order")
            _automation_step_tuple = extracted_method("_automation_step_tuple")
            _automation_sort_key = extracted_method("_automation_sort_key")
            _automation_sorted_steps = extracted_method("_automation_sorted_steps")
            _automation_step_from_entry = extracted_method("_automation_step_from_entry")
            _reconstruct_exact_automation_delta = extracted_method(
                "_reconstruct_exact_automation_delta"
            )

        linear = (0.5, 0.5, 0.5, 0.5)
        curved = (0.1, 0.8, 0.7, 0.9)
        baseline = tuple(
            (time_value, 0.125, 0.2, 0.0, time_value + 1, time_value + 1,
             True, *(curved if time_value == 1 else linear))
            for time_value in range(3)
        )
        insertion = (
            "3.000000:0.125000:0.700000:0.000000:4:4:1:"
            "0.500000000:0.500000000:0.500000000:0.500000000"
        )

        final_steps, intervals = Harness()._reconstruct_exact_automation_delta(
            baseline,
            ["I:3:" + insertion],
            (0.0, 4.0)
        )

        self.assertEqual(len(final_steps), 4)
        self.assertEqual(intervals, ((1.0, 3.0),))

        chained_baseline = tuple(
            tuple(list(step[:7]) + list(curved if step[0] == 0 else step[7:]))
            for step in baseline
        )
        _final_steps, chained_intervals = Harness()._reconstruct_exact_automation_delta(
            chained_baseline,
            ["I:3:" + insertion],
            (0.0, 4.0)
        )
        self.assertEqual(chained_intervals, ((0.0, 3.0),))

        deletion_baseline = tuple(
            (time_value, 0.125, 0.2, 0.0, time_value + 1, time_value + 1,
             True, *(curved if time_value == 1 else linear))
            for time_value in range(5)
        )
        _final_steps, deletion_intervals = Harness()._reconstruct_exact_automation_delta(
            deletion_baseline,
            ["D:3"],
            (0.0, 4.0)
        )
        self.assertEqual(deletion_intervals, ((1.0, 4.0),))

    def test_exact_delta_deleting_last_event_reports_an_empty_envelope(self):
        class Harness:
            _send_exact_automation_delta_response = extracted_method(
                "_send_exact_automation_delta_response"
            )

            def __init__(self):
                self.response = None

            def _parameter_normalized_value(self, _parameter):
                return 0.4

            def _automation_response_fields(self, *_args, **_kwargs):
                return ["0", "0.000000", "0.000000", "5", "patch", "1"]

            def _send_sys_ex_message(self, response, manufacturer):
                self.response = (response, manufacturer)

        context = {
            "control_index": 0,
            "device_param": object(),
            "clip": object(),
            "domain": (0.0, 4.0),
        }
        harness = Harness()
        harness._send_exact_automation_delta_response(
            context, object(), (), "REV", ((1.0, 1.0),), "5"
        )
        self.assertTrue(harness.response[0].startswith("0|0|0.400000|"))
        self.assertEqual(harness.response[1], 0x31)

    def test_exact_delta_multiple_intervals_share_one_undo_group(self):
        class Harness:
            _apply_exact_automation_delta = extracted_method(
                "_apply_exact_automation_delta"
            )

            def __init__(self):
                self.begin_count = 0
                self.end_count = 0
                self.writes = []
                self.reenable_count = 0

            def _begin_undo_step(self):
                self.begin_count += 1
                return True

            def _end_undo_step(self, started):
                if started:
                    self.end_count += 1

            def _write_exact_automation_events_to_envelope(
                    self, _envelope, _parameter, start, end, steps,
                    allow_empty=False, endpoint_padding=0.0001):
                self.writes.append((start, end, tuple(steps), allow_empty, endpoint_padding))
                return True

            def _parameter_automation_is_enabled(self, _parameter):
                return False

            def _re_enable_parameter_automation(self, _parameter):
                self.assert_undo_is_open = self.begin_count > self.end_count
                self.reenable_count += 1

        steps = (
            (1.0, 0.125, 0.2, 0.0, 0, 1, True, 0.5, 0.5, 0.5, 0.5),
            (6.0, 0.125, 0.8, 0.0, 0, 2, True, 0.5, 0.5, 0.5, 0.5),
        )
        harness = Harness()
        self.assertTrue(
            harness._apply_exact_automation_delta(
                {"device_param": object()}, object(), steps,
                ((0.0, 2.0), (5.0, 7.0)), True
            )
        )
        self.assertEqual(harness.begin_count, 1)
        self.assertEqual(harness.end_count, 1)
        self.assertEqual(harness.reenable_count, 1)
        self.assertTrue(harness.assert_undo_is_open)
        self.assertEqual(len(harness.writes), 2)
        self.assertTrue(all(write[4] == 0.0000001 for write in harness.writes))

    def test_exact_delta_pure_insert_creates_only_the_new_event(self):
        class Harness:
            _apply_direct_exact_automation_delta = extracted_method(
                "_apply_direct_exact_automation_delta"
            )

            def __init__(self):
                self.created = []
                self.begin_count = 0
                self.end_count = 0
                self.reenable_count = 0

            def _begin_undo_step(self):
                self.begin_count += 1
                return True

            def _end_undo_step(self, started):
                if started:
                    self.end_count += 1

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: step[0]))

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, _envelope, time_value, raw_value, step):
                self.created.append((time_value, raw_value, step[4]))

            def _parameter_automation_is_enabled(self, _parameter):
                return False

            def _re_enable_parameter_automation(self, _parameter):
                self.assert_undo_is_open = self.begin_count > self.end_count
                self.reenable_count += 1

            def _debug_log(self, message):
                raise AssertionError(message)

        baseline = (
            (0.0, 0.125, 0.2, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
            (1.0, 0.125, 0.8, 0.0, 2, 2, True, 0.1, 0.8, 0.7, 0.9),
        )
        inserted = (2.0, 0.125, 0.6, 0.0, 3, 3, True, 0.5, 0.5, 0.5, 0.5)
        harness = Harness()

        applied = harness._apply_direct_exact_automation_delta(
            {"device_param": object()},
            object(),
            baseline,
            baseline + (inserted,),
            ["I:2:ignored"],
            True
        )

        self.assertTrue(applied)
        self.assertEqual(harness.created, [(2.0, 0.6, 3)])
        self.assertEqual(harness.begin_count, 1)
        self.assertEqual(harness.end_count, 1)
        self.assertEqual(harness.reenable_count, 1)
        self.assertTrue(harness.assert_undo_is_open)

    def test_exact_delta_pure_unique_delete_removes_only_that_timestamp(self):
        class Envelope:
            def __init__(self):
                self.deleted = []

            def delete_events_in_range(self, start, end):
                self.deleted.append((start, end))

        class Harness:
            _apply_direct_exact_automation_delta = extracted_method(
                "_apply_direct_exact_automation_delta"
            )

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def _debug_log(self, message):
                raise AssertionError(message)

        baseline = tuple(
            (float(index), 0.125, 0.2, 0.0, index + 1, index + 1,
             True, 0.5, 0.5, 0.5, 0.5)
            for index in range(5)
        )
        envelope = Envelope()

        applied = Harness()._apply_direct_exact_automation_delta(
            {"device_param": object()},
            envelope,
            baseline,
            baseline[:3] + baseline[4:],
            ["D:3"]
        )

        self.assertTrue(applied)
        self.assertEqual(len(envelope.deleted), 1)
        self.assertAlmostEqual(envelope.deleted[0][0], 3.0 - 0.00001)
        self.assertAlmostEqual(envelope.deleted[0][1], 3.0 + 0.00001)

    def test_exact_delta_rebuilds_only_the_touched_vertical_group(self):
        class Envelope:
            def __init__(self):
                self.deleted = []

            def delete_events_in_range(self, start, end):
                self.deleted.append((start, end))

        class Harness:
            _apply_direct_exact_automation_delta = extracted_method(
                "_apply_direct_exact_automation_delta"
            )

            def __init__(self):
                self.created = []

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, _envelope, time_value, value, step):
                self.created.append((time_value, value, step[4]))

            def _debug_log(self, message):
                raise AssertionError(message)

        baseline = (
            (1.0, 0.125, 0.2, 0.0, 1, 1, True, 0.5, 0.5, 0.5, 0.5),
            (1.0, 0.125, 0.8, 0.0, 2, 2, True, 0.5, 0.5, 0.5, 0.5),
        )
        envelope = Envelope()
        harness = Harness()
        self.assertTrue(
            harness._apply_direct_exact_automation_delta(
                {"device_param": object()}, envelope, baseline,
                baseline[1:], ["D:0"]
            )
        )
        self.assertEqual(len(envelope.deleted), 1)
        self.assertEqual(harness.created, [(1.0, 0.8, 2)])

    def test_exact_delta_move_rewrites_only_its_old_and_new_event_groups(self):
        class Envelope:
            def __init__(self):
                self.deleted = []

            def delete_events_in_range(self, start, end):
                self.deleted.append((start, end))

        class Harness:
            _apply_direct_exact_automation_delta = extracted_method(
                "_apply_direct_exact_automation_delta"
            )

            def __init__(self):
                self.created = []

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def _parameter_target_value_from_normalized(self, _parameter, value):
                return value

            def _create_automation_event(self, _envelope, time_value, value, step):
                self.created.append((time_value, value, step[4]))

            def _debug_log(self, message):
                raise AssertionError(message)

        baseline = (
            (0.0, 0.125, 0.2, 0.0, 1, 1, True, 0.1, 0.2, 0.8, 0.9),
            (1.0, 0.125, 0.5, 0.0, 2, 2, True, 0.2, 0.3, 0.7, 0.8),
            (3.0, 0.125, 0.8, 0.0, 3, 3, True, 0.3, 0.4, 0.6, 0.7),
        )
        moved = tuple(list(baseline[1][:1]) + list(baseline[1][1:]))
        moved = tuple([2.0] + list(moved[1:]))
        final_steps = (baseline[0], moved, baseline[2])
        envelope = Envelope()
        harness = Harness()

        self.assertTrue(
            harness._apply_direct_exact_automation_delta(
                {"device_param": object()}, envelope, baseline, final_steps,
                ["R:1:1:ignored"]
            )
        )
        self.assertEqual(len(envelope.deleted), 1)
        self.assertAlmostEqual(envelope.deleted[0][0], 1.0 - 0.00001)
        self.assertEqual(harness.created, [(2.0, 0.5, 2)])

    def test_exact_delta_acceptance_rereads_only_the_changed_range(self):
        class Harness:
            _accepted_exact_automation_delta_snapshot = extracted_method(
                "_accepted_exact_automation_delta_snapshot"
            )
            _automation_steps_preserving_unchanged_vertical_values = extracted_method(
                "_automation_steps_preserving_unchanged_vertical_values"
            )

            def __init__(self):
                self.reads = []

            def _automation_steps_from_envelope_events(
                    self, _envelope, _parameter, start, length, _duration):
                self.reads.append((start, length))
                return tuple(
                    (time_value, 0.125, 0.75, 0.0, 0, index + 1,
                     True, 0.5, 0.5, 0.5, 0.5)
                    for index, time_value in enumerate((149.0, 150.0, 151.0))
                )

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: (step[0], step[5])))

            def _automation_step_tuple(self, step, _index=0):
                return tuple(step)

        intended = tuple(
            (float(index), 0.125, 0.5, 0.0, 0, index + 1,
             True, 0.5, 0.5, 0.5, 0.5)
            for index in range(300)
        )
        harness = Harness()
        accepted = harness._accepted_exact_automation_delta_snapshot(
            {"device_param": object()}, object(), intended,
            ((149.0, 151.0),), 0.125
        )
        self.assertEqual(harness.reads, [(149.0, 2.0)])
        self.assertEqual(len(accepted), 300)
        self.assertEqual(accepted[150][2], 0.75)

    def test_exact_delta_normalizes_only_events_inside_the_changed_range(self):
        controls = type("Controls", (), {
            "x1": 0.5, "y1": 0.5, "x2": 0.5, "y2": 0.5,
        })()
        events = tuple(
            type("Event", (), {
                "time": float(index),
                "value": float(index) / 299.0,
                "control_coefficients": controls,
            })()
            for index in range(300)
        )

        class Envelope:
            def __init__(self):
                self.ranges = []
                self.value_calls = []

            def events_in_range(self, start, end):
                self.ranges.append((start, end))
                return tuple(
                    event for event in events
                    if event.time >= start and event.time <= end
                )

            def value_at_time(self, time_value):
                self.value_calls.append(time_value)
                return float(time_value) / 299.0

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _ordered_same_time_automation_events = extracted_method(
                "_ordered_same_time_automation_events"
            )
            _automation_event_records = extracted_method(
                "_automation_event_records"
            )
            _automation_event_fingerprint_from_records = extracted_method(
                "_automation_event_fingerprint_from_records"
            )
            _remember_automation_event_read = extracted_method(
                "_remember_automation_event_read"
            )
            _cached_automation_event_read = extracted_method(
                "_cached_automation_event_read"
            )
            _automation_steps_from_envelope_events = extracted_method(
                "_automation_steps_from_envelope_events"
            )
            _parameter_domain_values_from_envelope_events = extracted_method(
                "_parameter_domain_values_from_envelope_events"
            )
            _parameter_normalized_value_from_raw = extracted_method(
                "_parameter_normalized_value_from_raw"
            )
            _accepted_exact_automation_delta_snapshot = extracted_method(
                "_accepted_exact_automation_delta_snapshot"
            )
            _automation_steps_preserving_unchanged_vertical_values = extracted_method(
                "_automation_steps_preserving_unchanged_vertical_values"
            )

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: (step[0], step[5])))

            def _automation_step_tuple(self, step, _index=0):
                return tuple(step)

            def _debug_log(self, message):
                raise AssertionError(message)

        intended = tuple(
            (float(index), 0.125, float(index) / 299.0, 0.0, 0, index + 1,
             True, 0.5, 0.5, 0.5, 0.5)
            for index in range(300)
        )
        envelope = Envelope()
        accepted, raw_records = Harness()._accepted_exact_automation_delta_snapshot(
            {"device_param": type("Parameter", (), {"min": 0.0, "max": 1.0})()},
            envelope,
            intended,
            ((149.0, 151.0),),
            0.125,
            include_live_event_records=True
        )

        self.assertEqual(envelope.ranges, [(149.0, 151.0000001)])
        self.assertEqual(envelope.value_calls, [149.0, 150.0, 151.0])
        self.assertEqual(len(accepted), 300)
        self.assertEqual(len(raw_records), 3)

    def test_exact_delta_raw_fingerprint_is_patched_without_a_full_reread(self):
        class Harness:
            _merged_automation_event_records = extracted_method(
                "_merged_automation_event_records"
            )
            _automation_event_fingerprint_from_records = extracted_method(
                "_automation_event_fingerprint_from_records"
            )

        records = tuple(
            (float(index), 0.5, 0.5, 0.5, 0.5, 0.5)
            for index in range(300)
        )
        patch = (
            (149.0, 0.25, 0.1, 0.2, 0.3, 0.4),
            (150.0, 0.75, 0.6, 0.7, 0.8, 0.9),
            (151.0, 0.25, 0.2, 0.3, 0.4, 0.5),
        )
        harness = Harness()
        merged = harness._merged_automation_event_records(
            records, patch, ((149.0, 151.0),)
        )

        self.assertEqual(len(merged), 300)
        self.assertEqual(merged[149:152], patch)
        self.assertNotEqual(
            harness._automation_event_fingerprint_from_records(records),
            harness._automation_event_fingerprint_from_records(merged)
        )

    def test_stale_exact_delta_is_rejected_before_any_mutation(self):
        class Harness:
            _handle_exact_automation_delta = extracted_method(
                "_handle_exact_automation_delta"
            )

            def __init__(self):
                self.errors = []
                self.applied = False

            def _automation_payload_checksum(self, value):
                checksum = 0
                for byte in value.encode("ascii"):
                    checksum = ((checksum * 31) + byte) & 0x7fffffff
                return checksum

            def _automation_trace(self, *_args):
                pass

            def _resolve_automation_context(self, _token, _revision):
                return ({"control_index": 0}, object(), (), "NEW", "stale")

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

            def _reconstruct_exact_automation_delta(self, *_args):
                self.applied = True

        fields = ["D", "0", "CTX", "OLD", "0.125000", "D:0"]
        checksum = Harness()._automation_payload_checksum("|".join(fields))
        fields += ["1", "{:08X}".format(checksum), "9"]
        harness = Harness()
        harness._handle_exact_automation_delta(fields)
        self.assertFalse(harness.applied)
        self.assertEqual(harness.errors[0][1]["status"], "stale")

    def test_corrupted_exact_delta_is_retryable_transport_failure(self):
        class Harness:
            _handle_exact_automation_delta = extracted_method(
                "_handle_exact_automation_delta"
            )

            def __init__(self):
                self._automation_trace_pending_transfer = {
                    "token": "19", "dial": 4, "kind": "D",
                    "count1": 1, "checksum": 0x12345678,
                }
                self.errors = []

            def _automation_payload_checksum(self, _value):
                return 0x76543210

            def _automation_trace(self, *_args):
                pass

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

        harness = Harness()
        harness._handle_exact_automation_delta([
            "D", "4", "CTX", "REV", "0.125000", "D:0",
            "1", "12345678", "19",
        ])

        self.assertIsNone(harness._automation_trace_pending_transfer)
        self.assertEqual(harness.errors, [((4, "19"), {"status": "transport"})])

    def test_exact_delta_uses_only_the_pointwise_writer(self):
        class Harness:
            _handle_exact_automation_delta = extracted_method(
                "_handle_exact_automation_delta"
            )

            def __init__(self):
                self._automation_trace_pending_transfer = None
                self.direct_write = None
                self.response = None
                self.traces = []
                self.stored = None

            def _automation_payload_checksum(self, value):
                checksum = 0
                for byte in value.encode("ascii"):
                    checksum = ((checksum * 31) + byte) & 0x7fffffff
                return checksum

            def _automation_trace(self, transaction, stage, details=""):
                self.traces.append((transaction, stage, details))

            def _resolve_automation_context(self, _token, _revision):
                return ({
                    "control_index": 2,
                    "domain": (0.0, 4.0),
                    "clip": object(),
                    "device_param": object(),
                    "live_event_records": (),
                }, object(), ("baseline",), "OLD", "ok")

            def _reconstruct_exact_automation_delta(
                    self, _baseline, _entries, _domain):
                return ((
                    (0.0, 0.125, 0.2, 0.0, 1, 1, True,
                     0.5, 0.5, 0.5, 0.5),
                    (1.0, 0.125, 0.4, 0.0, 2, 2, True,
                     0.1, 0.8, 0.7, 0.9),
                    (2.0, 0.125, 0.6, 0.0, 3, 3, True,
                     0.5, 0.5, 0.5, 0.5),
                    (4.0, 0.125, 0.8, 0.0, 4, 4, True,
                     0.5, 0.5, 0.5, 0.5),
                ), ((0.0, 2.0),))

            def _parameter_automation_is_enabled(self, _parameter):
                return False

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _apply_direct_exact_automation_delta(
                    self, context, envelope, baseline, final_steps, entries,
                    automation_should_re_enable=False):
                self.direct_write = (
                    context, envelope, baseline, final_steps, tuple(entries),
                    automation_should_re_enable
                )
                return True

            def _accepted_exact_automation_delta_snapshot(
                    self, _context, _envelope, final_steps, _intervals,
                    _duration, include_live_event_records=False):
                self.assert_live_records = include_live_event_records
                return (tuple(final_steps), ((0.0, "event"),))

            def _automation_snapshot_revision(self, *_args):
                return "NEW"

            def _merged_automation_event_records(self, *_args):
                return ((0.0, "event"),)

            def _automation_event_fingerprint_from_records(self, records):
                return ("fingerprint", tuple(records))

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _store_authored_automation_steps(self, *_args):
                self.stored = _args[-1]

            def _send_exact_automation_delta_response(self, *args):
                self.response = args

            def _re_enable_after_automation_write(self, *_args):
                pass

            def _refresh_parameter_metadata_on_automation_change(self):
                pass

            def _handle_exact_automation_full_write(
                    self, fields, compact_response=False, write_intervals=None,
                    audit_steps=None):
                raise AssertionError("a point edit must not use the shape writer")

            def _automation_write_error_response(self, *_args, **_kwargs):
                raise AssertionError("valid delta must not be rejected")

        fields = ["D", "2", "CTX", "OLD", "0.125000", "R:0:0:entry"]
        checksum = Harness()._automation_payload_checksum("|".join(fields))
        fields += ["1", "{:08X}".format(checksum), "44"]
        harness = Harness()
        harness._handle_exact_automation_delta(fields)

        self.assertIsNotNone(harness.direct_write)
        self.assertEqual(harness.direct_write[2], ("baseline",))
        self.assertEqual(harness.direct_write[4], ("R:0:0:entry",))
        self.assertTrue(harness.direct_write[5])
        self.assertTrue(harness.assert_live_records)
        self.assertEqual(harness.stored[-1][0], 4.0)
        self.assertEqual(harness.response[3], "NEW")
        self.assertEqual(harness.response[-1], "44")
        self.assertIn(
            "delta_write_direct",
            [stage for _transaction, stage, _details in harness.traces]
        )

    def test_repeating_exact_write_expands_one_cycle_before_live_write(self):
        class Harness:
            AUTOMATION_REPEATING_PATTERN_MAX_EXPANDED_EVENTS = 262144
            _automation_step_id = extracted_method("_automation_step_id")
            _automation_step_order = extracted_method("_automation_step_order")
            _automation_step_tuple = extracted_method("_automation_step_tuple")
            _automation_sort_key = extracted_method("_automation_sort_key")
            _automation_sorted_steps = extracted_method("_automation_sorted_steps")
            _automation_step_entry = extracted_method("_automation_step_entry")
            _automation_step_from_entry = extracted_method("_automation_step_from_entry")
            _automation_payload_checksum = extracted_method("_automation_payload_checksum")
            _handle_repeating_exact_automation_full_write = extracted_method(
                "_handle_repeating_exact_automation_full_write"
            )

            def __init__(self):
                self.forwarded = None
                self.errors = []

            def _handle_exact_automation_full_write(self, fields, compact_response=False):
                self.forwarded = (fields, compact_response)

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

        exact = ":1:0.500000000:0.500000000:0.500000000:0.500000000"
        # A phase-shifted saw: the finite start owns the split point, the core
        # repeats only authored verticals, and the suffix replaces the final
        # vertical plus its clipped endpoint.
        start = "0.000000:0.062500:0.250000:0.000000:0:1" + exact
        cycle = ",".join((
            "0.187500:0.062500:1.000000:0.000000:0:1" + exact,
            "0.187500:0.062500:0.000000:0.000000:0:2" + exact,
        ))
        end = ",".join((
            "0.937500:0.062500:1.000000:0.000000:0:1" + exact,
            "0.937500:0.062500:0.000000:0.000000:0:2" + exact,
            "1.000000:0.062500:0.250000:0.000000:0:3" + exact,
        ))
        base_fields = [
            "R", "2", "CTX", "REV", "0.000000", "1.000000", "0.003906",
            "0.000000000000", "0.250000000000", start, cycle, end,
        ]
        harness = Harness()
        checksum = harness._automation_payload_checksum("|".join(base_fields))
        fields = base_fields + ["1", "2", "3", "10", "{:08X}".format(checksum), "12"]

        harness._handle_repeating_exact_automation_full_write(fields)

        self.assertEqual(harness.errors, [])
        self.assertIsNotNone(harness.forwarded)
        forwarded, compact_response = harness.forwarded
        self.assertTrue(compact_response)
        self.assertEqual(forwarded[0], "F")
        self.assertEqual(forwarded[8], "10")
        expanded_entries = forwarded[7].split(",")
        self.assertEqual(
            [float(entry.split(":", 1)[0]) for entry in expanded_entries],
            [
                0.0, 0.1875, 0.1875,
                0.4375, 0.4375,
                0.6875, 0.6875,
                0.9375, 0.9375,
                1.0,
            ]
        )

    def test_repeating_exact_write_rejects_a_bad_expanded_count(self):
        class Harness:
            AUTOMATION_REPEATING_PATTERN_MAX_EXPANDED_EVENTS = 262144
            _automation_step_id = extracted_method("_automation_step_id")
            _automation_step_order = extracted_method("_automation_step_order")
            _automation_step_tuple = extracted_method("_automation_step_tuple")
            _automation_sort_key = extracted_method("_automation_sort_key")
            _automation_sorted_steps = extracted_method("_automation_sorted_steps")
            _automation_step_entry = extracted_method("_automation_step_entry")
            _automation_step_from_entry = extracted_method("_automation_step_from_entry")
            _automation_payload_checksum = extracted_method("_automation_payload_checksum")
            _handle_repeating_exact_automation_full_write = extracted_method(
                "_handle_repeating_exact_automation_full_write"
            )

            def __init__(self):
                self.forwarded = False
                self.errors = []

            def _handle_exact_automation_full_write(self, *_args, **_kwargs):
                self.forwarded = True

            def _automation_write_error_response(self, *args, **kwargs):
                self.errors.append((args, kwargs))

        exact = ":1:0.500000000:0.500000000:0.500000000:0.500000000"
        entry = "0.000000:0.062500:0.500000:0.000000:0:1" + exact
        end = "1.000000:0.062500:0.500000:0.000000:0:1" + exact
        base_fields = [
            "R", "2", "CTX", "REV", "0.000000", "1.000000", "0.003906",
            "0.000000000000", "0.250000000000", entry, entry, end,
        ]
        harness = Harness()
        checksum = harness._automation_payload_checksum("|".join(base_fields))
        fields = base_fields + ["1", "1", "1", "999", "{:08X}".format(checksum), "12"]

        harness._handle_repeating_exact_automation_full_write(fields)

        self.assertFalse(harness.forwarded)
        self.assertEqual(len(harness.errors), 1)

    def test_automation_context_keeps_original_parameter_after_bank_change(self):
        parameter_a = type("Parameter", (), {"automation_state": 1})()
        parameter_b = type("Parameter", (), {"automation_state": 1})()
        envelope_a = object()

        class Clip:
            def automation_envelope(self, parameter):
                self.requested_parameter = parameter
                return envelope_a

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()

        class Harness:
            AUTOMATION_CONTEXT_MAX_AGE = 180.0
            _resolve_automation_context = extracted_method(
                "_resolve_automation_context"
            )

            def __init__(self):
                now = time.monotonic()
                self._automation_contexts = {
                    "CTX": {
                        "token": "CTX",
                        "clip_slot": slot,
                        "clip_slot_identity": id(slot),
                        "clip": clip,
                        "clip_identity": id(clip),
                        "device_param": parameter_a,
                        "parameter_identity": id(parameter_a),
                        "point_duration": 0.125,
                        "last_activity": now,
                    }
                }
                self.current_bank_parameter = parameter_b

            def _expire_automation_contexts(self):
                pass

            def _live_object_identity(self, value):
                return id(value)

            def _parameter_is_automatable(self, parameter):
                return parameter is not None and hasattr(parameter, "automation_state")

            def _automation_domain_for_clip(self, _clip, _parameter):
                return (0.0, 4.0)

            def _automation_envelope_supports_point_events(self, _envelope):
                return False

            def _automation_sorted_steps(self, steps):
                return tuple(steps)

            def _automation_snapshot_revision(self, _clip, parameter, _domain, _steps):
                return "A" if parameter is parameter_a else "B"

        harness = Harness()
        context, envelope, _steps, revision, status = harness._resolve_automation_context("CTX")
        self.assertEqual(status, "ok")
        self.assertIs(context["device_param"], parameter_a)
        self.assertIs(clip.requested_parameter, parameter_a)
        self.assertIs(envelope, envelope_a)
        self.assertEqual(revision, "A")

    def test_exact_context_validation_avoids_per_event_value_sampling(self):
        controls = type("Controls", (), {
            "x1": 0.5, "y1": 0.5, "x2": 0.5, "y2": 0.5,
        })()
        events = tuple(
            type("Event", (), {
                # Include a real same-time vertical pair: raw fingerprint
                # validation must not sample even that pair.
                "time": 0.0 if index < 2 else float(index - 1),
                "value": float(index) / 300.0,
                "control_coefficients": controls,
            })()
            for index in range(300)
        )

        class Envelope:
            def __init__(self):
                self.value_calls = 0

            def events_in_range(self, _start, _end):
                return events

            def value_at_time(self, _time):
                self.value_calls += 1
                return 0.5

        envelope = Envelope()
        parameter = type("Parameter", (), {"automation_state": 1})()

        class Clip:
            def automation_envelope(self, _parameter):
                return envelope

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()

        class Harness:
            _automation_events_in_closed_range = extracted_method(
                "_automation_events_in_closed_range"
            )
            _ordered_same_time_automation_events = extracted_method(
                "_ordered_same_time_automation_events"
            )
            _automation_live_event_fingerprint = extracted_method(
                "_automation_live_event_fingerprint"
            )
            _automation_event_records = extracted_method(
                "_automation_event_records"
            )
            _automation_event_fingerprint_from_records = extracted_method(
                "_automation_event_fingerprint_from_records"
            )
            _remember_automation_event_read = extracted_method(
                "_remember_automation_event_read"
            )
            _cached_automation_event_read = extracted_method(
                "_cached_automation_event_read"
            )
            _resolve_automation_context = extracted_method(
                "_resolve_automation_context"
            )

            def __init__(self):
                self._automation_contexts = {}

            def _expire_automation_contexts(self):
                pass

            def _live_object_identity(self, value):
                return id(value)

            def _parameter_is_automatable(self, value):
                return value is parameter

            def _automation_domain_for_clip(self, _clip, _parameter):
                return (0.0, 299.0)

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _automation_runtime_supports_point_events(self):
                return True

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        fingerprint = harness._automation_live_event_fingerprint(
            envelope, (0.0, 299.0), 0.125
        )
        harness._automation_contexts["CTX"] = {
            "token": "CTX",
            "clip_slot": slot,
            "clip_slot_identity": id(slot),
            "clip": clip,
            "clip_identity": id(clip),
            "device_param": parameter,
            "parameter_identity": id(parameter),
            "point_duration": 0.125,
            "domain": (0.0, 299.0),
            "snapshot": (),
            "revision": "REV",
            "live_fingerprint": fingerprint,
            "last_activity": time.monotonic(),
        }
        envelope.value_calls = 0
        _context, _envelope, _steps, revision, status = harness._resolve_automation_context(
            "CTX", "REV"
        )
        self.assertEqual(status, "ok")
        self.assertEqual(revision, "REV")
        self.assertEqual(envelope.value_calls, 0)

    def test_audio_automation_domain_includes_markers_source_and_warp_extremes(self):
        class Harness:
            _automation_domain_for_clip = extracted_method(
                "_automation_domain_for_clip"
            )

            def _decoupled_automation_info(self, _clip, _parameter):
                return None

            def _audio_clip_sample_end(self, _clip):
                return 19.0

        markers = (
            type("WarpMarker", (), {"beat_time": -3.0})(),
            type("WarpMarker", (), {"beat_time": 21.0})(),
        )
        clip = type("AudioClip", (), {
            "is_audio_clip": True,
            "start_time": -1.0,
            "start_marker": 2.0,
            "loop_start": 4.0,
            "length": 12.0,
            "end_marker": 10.0,
            "loop_end": 8.0,
            "warp_markers": markers,
        })()
        self.assertEqual(
            Harness()._automation_domain_for_clip(clip, object()),
            (-3.0, 21.0)
        )

    def test_exact_pencil_events_make_linear_points_with_vertical_boundary_guards(self):
        class Envelope:
            def __init__(self):
                self.deleted = []

            def value_at_time(self, _time):
                return 0.0

            def delete_events_in_range(self, start, end):
                self.deleted.append((start, end))

        class Harness:
            _write_incremental_automation_pencil_event_interval = extracted_method(
                "_write_incremental_automation_pencil_event_interval"
            )

            def __init__(self):
                self.created = []
                self.decoupled_info = None

            def _automation_envelope_supports_point_events(self, _envelope):
                return True

            def _decoupled_automation_info(self, _clip, _parameter):
                return self.decoupled_info

            def _positive_mod(self, value, modulus):
                return value % modulus

            def _create_linear_automation_event(self, _envelope, time_value, raw_value):
                self.created.append((time_value, raw_value))

            def _parameter_target_value_from_normalized(self, parameter, value):
                return parameter.min + ((parameter.max - parameter.min) * value)

        envelope = Envelope()
        harness = Harness()
        state = {
            "envelope": envelope,
            "device_param": type("Parameter", (), {"min": -48.0, "max": 48.0})(),
            "clip": object(),
            "loop_start": 0.0,
            "loop_end": 4.0,
        }
        point_a = (1.0, 0.03125, 0.2, 0.0, 20, 20)
        point_b = (1.5, 0.03125, 0.8, 0.0, 21, 21)

        self.assertTrue(
            harness._write_incremental_automation_pencil_event_interval(
                state, point_a, point_b
            )
        )
        self.assertEqual(envelope.deleted, [(0.9999, 1.5001)])
        self.assertEqual(
            [time_value for time_value, _raw_value in harness.created],
            [0.9999, 1.0, 1.5, 1.5001]
        )
        for (_, actual), expected in zip(harness.created, (0.0, -28.8, 28.8, 0.0)):
            self.assertAlmostEqual(actual, expected)

        envelope.deleted = []
        harness.created = []
        harness.decoupled_info = {
            "note_start": 0.0,
            "automation_length": 1.0,
            "physical_length": 2.0,
            "physical_end": 2.0,
        }
        wrapped_a = (0.25, 0.03125, 0.2, 0.0, 20, 20)
        wrapped_b = (0.5, 0.03125, 0.8, 0.0, 21, 21)
        self.assertTrue(
            harness._write_incremental_automation_pencil_event_interval(
                state, wrapped_a, wrapped_b
            )
        )
        self.assertEqual(
            envelope.deleted,
            [(0.2499, 0.5001), (1.2499, 1.5001)]
        )
        self.assertEqual(
            [time_value for time_value, _ in harness.created],
            [0.2499, 0.25, 0.5, 0.5001, 1.2499, 1.25, 1.5, 1.5001]
        )

    def test_incremental_pencil_writes_only_the_new_physical_interval(self):
        class Envelope:
            def __init__(self):
                self.inserted = []

            def insert_step(self, time_value, duration, value):
                self.inserted.append((time_value, duration, value))

        harness = AutomationPencilWriterHarness()
        envelope = Envelope()
        state = {
            "envelope": envelope,
            "device_param": object(),
            "clip": object(),
            "loop_end": 4.0,
            "sample_duration": 0.25,
            "point_duration": 0.5,
        }
        point_a = (1.0, 0.5, 0.2, 0.0, 20, 20)
        point_b = (1.5, 0.5, 0.8, 0.0, 21, 21)

        self.assertTrue(harness._write_incremental_automation_pencil_interval(state, None, point_a))
        self.assertEqual([entry[0] for entry in envelope.inserted], [1.0])

        envelope.inserted = []
        self.assertTrue(harness._write_incremental_automation_pencil_interval(state, point_a, point_b))
        self.assertEqual([entry[0] for entry in envelope.inserted], [1.0, 1.25, 1.5])
        self.assertEqual(harness.neutralized[-1][:2], (1.0, 1.5))
        self.assertEqual(harness.logs, [])

    def test_incremental_pencil_keeps_completed_point_and_replaces_only_new_interval(self):
        harness = AutomationPencilMergeHarness()
        original = (
            (0.0, 0.03125, 0.1, 0.0, 1, 1),
            (0.5, 0.03125, 0.4, 0.0, 2, 2),
            (1.0, 0.03125, 0.7, 0.0, 3, 3),
            (1.5, 0.03125, 0.9, 0.0, 4, 4),
        )
        point_a = (0.5, 0.03125, 0.2, 0.0, 20, 20)
        after_a = harness._merge_incremental_automation_pencil_point(original, None, point_a)
        point_b = (1.0, 0.03125, 0.8, 0.0, 21, 21)
        after_b = harness._merge_incremental_automation_pencil_point(after_a, point_a, point_b)

        self.assertEqual([step[0] for step in after_b], [0.0, 0.5, 1.0, 1.5])
        self.assertEqual(next(step for step in after_b if step[0] == 0.5), point_a)
        self.assertEqual(next(step for step in after_b if step[0] == 1.0), point_b)
        self.assertEqual(next(step for step in after_b if step[0] == 1.5), original[-1])

    def test_incremental_pencil_break_preserves_entries_and_resets_interpolation(self):
        class Harness:
            _handle_automation_pencil_message = extracted_method(
                "_handle_automation_pencil_message"
            )

            def __init__(self):
                self._automation_pencil_stroke = {
                    "stroke_id": 12,
                    "last_point": (1.0, 0.03125, 0.5, 0.0, 9, 9),
                    "entries": ["1:1.000000:0.500000:9:9"],
                }

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        harness._handle_automation_pencil_message(["P", "R", "12"])

        self.assertIsNone(harness._automation_pencil_stroke["last_point"])
        self.assertEqual(
            harness._automation_pencil_stroke["entries"],
            ["1:1.000000:0.500000:9:9"]
        )

    def test_flin_column_velocity_deviation_uses_the_eighth_wire_field(self):
        harness = FlinColumnHarness()
        payload = b"v2|column|0|3|101|82|4|-27"
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

    def test_automation_trace_is_quiet_without_the_diagnostic_switch(self):
        class Harness:
            _automation_trace = extracted_method("_automation_trace")

            def __init__(self):
                self.logs = []

            def log_message(self, message):
                self.logs.append(message)

        harness = Harness()
        harness._automation_trace("77", "delta_audit", "exact=1")
        self.assertEqual(harness.logs, [])

    def test_automation_trace_correlates_app_intent_with_received_chunk_counts(self):
        harness = AutomationTransferTraceHarness()
        trace_payload = "T|77|2|S|4|3|2|10|3|00ABCDEF"
        harness._set_automation_envelope(
            [0xF0, 0x32, *trace_payload.encode("ascii"), 0xF7]
        )
        self.assertEqual(
            harness._automation_trace_pending_transfer["token"], "77"
        )

        payload = list(b"S|77|shape")
        harness.handle_sysex([0xF0, 0x32, ord("$"), *payload[:3], 0xF7])
        harness.handle_sysex([0xF0, 0x32, ord("$"), *payload[3:7], 0xF7])
        harness.handle_sysex([0xF0, 0x32, ord("_"), *payload[7:], 0xF7])

        self.assertEqual(
            harness.received,
            [[0xF0, 0x32, *payload, 0xF7]]
        )
        self.assertTrue(any(
            "tx=77 stage=app_intent" in entry for entry in harness.logs
        ))
        self.assertTrue(any(
            "tx=77 stage=chunk_start" in entry for entry in harness.logs
        ))
        self.assertTrue(any(
            "tx=77 stage=chunk_final" in entry
            and "packets=3" in entry
            and "bytes=10" in entry
            and "packet_match=1" in entry
            and "byte_match=1" in entry
            for entry in harness.logs
        ))

        harness.received = []
        harness.logs = []
        harness._set_automation_envelope(
            [0xF0, 0x32, *trace_payload.encode("ascii"), 0xF7]
        )
        harness.handle_sysex([0xF0, 0x32, ord("$"), *payload[:4], 0xF7])
        harness.handle_sysex([0xF0, 0x32, ord("_"), *payload[7:], 0xF7])
        self.assertTrue(any(
            "stage=chunk_final" in entry
            and "packets=2" in entry
            and "bytes=7" in entry
            and "packet_match=0" in entry
            and "byte_match=0" in entry
            for entry in harness.logs
        ))

    def test_automation_trace_accepts_compact_delta_intent(self):
        harness = AutomationTransferTraceHarness()
        trace_payload = "T|81|5|D|6|0|0|479|10|31659FAD"
        harness._set_automation_envelope(
            [0xF0, 0x32, *trace_payload.encode("ascii"), 0xF7]
        )

        self.assertEqual(
            harness._automation_trace_pending_transfer,
            {
                "token": "81",
                "dial": 5,
                "kind": "D",
                "count1": 6,
                "count2": 0,
                "count3": 0,
                "payload_bytes": 479,
                "packet_count": 10,
                "checksum": 0x31659FAD,
            }
        )

    def test_generated_binary_shape_survives_two_short_chunks_exactly(self):
        harness = AutomationTransferTraceHarness()
        payload = [0x47, 1, 0] + [
            (index * 37) & 0x7F for index in range(76)
        ]

        harness.handle_sysex([
            0xF0, 0x32, ord("$"), *payload[:48], 0xF7
        ])
        harness.handle_sysex([
            0xF0, 0x32, ord("_"), *payload[48:], 0xF7
        ])

        self.assertEqual(
            harness.received,
            [[0xF0, 0x32, *payload, 0xF7]]
        )

    def test_single_final_chunk_is_a_complete_transfer(self):
        harness = SysExHarness()
        record = [1] * 11
        harness.handle_sysex([0xF0, 14, ord("_"), *record, 0xF7])
        self.assertEqual(harness.received, [[0xF0, 14, *record, 0xF7]])

    def test_single_final_native_note_transfer_is_not_dropped(self):
        harness = SysExHarness()
        command = note_transfer_message("duplicate", 9, 2000, [0x12345])
        harness.handle_sysex([0xF0, 0x5C, ord("_"), *command[2:-1], 0xF7])
        self.assertEqual(harness.received, [command])

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

    def test_large_binary_metadata_uses_bounded_ordered_chunks(self):
        class Harness:
            SYSEX_OUTGOING_MAX_CHUNK_LENGTH = 240
            _send_chunked_binary_sys_ex_message = extracted_method(
                "_send_chunked_binary_sys_ex_message"
            )

            def __init__(self):
                self.messages = []

            def _send_midi(self, message):
                self.messages.append(tuple(message))

        payload = tuple(index & 0x7F for index in range(600))
        harness = Harness()
        harness._send_chunked_binary_sys_ex_message(payload, 0x0E)

        self.assertEqual(len(harness.messages), 3)
        self.assertEqual(
            [message[3] for message in harness.messages],
            [ord("$"), ord("$"), ord("_")]
        )
        self.assertTrue(all(len(message[4:-1]) <= 240 for message in harness.messages))
        self.assertEqual(
            tuple(byte for message in harness.messages for byte in message[4:-1]),
            payload
        )

        direct = Harness()
        direct._send_chunked_binary_sys_ex_message((1, 2, 3), 0x0E)
        self.assertEqual(direct.messages, [(0xF0, 0x0E, 0x01, ord("!"), 1, 2, 3, 0xF7)])

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

    def test_native_note_duplicate_preserves_live_owned_expression(self):
        expression = object()
        note = type("Note", (), {
            "note_id": 0x12345,
            "start_time": 1.0,
            "expression": expression,
        })()

        class Clip:
            is_midi_clip = True
            start_time = 0.0
            start_marker = 0.0
            loop_start = 0.0
            loop_end = 4.0
            end_marker = 4.0
            length = 4.0

            def __init__(self):
                self.notes = [note]

            def get_notes_by_id(self, note_ids):
                return tuple(item for item in self.notes if item.note_id in note_ids)

            def get_notes_extended(self, _pitch, _pitch_span, start, span):
                end = start + span
                return tuple(item for item in self.notes if start <= item.start_time < end)

            def get_all_notes_extended(self):
                return tuple(self.notes)

            def duplicate_notes_by_id(self, note_ids, destination_time):
                earliest = min(item.start_time for item in self.notes if item.note_id in note_ids)
                added = []
                for source in [item for item in self.notes if item.note_id in note_ids]:
                    clone = type("Note", (), {
                        "note_id": source.note_id + 1_000_000,
                        "start_time": destination_time + source.start_time - earliest,
                        "expression": source.expression,
                    })()
                    self.notes.append(clone)
                    added.append(clone.note_id)
                return tuple(added)

        clip = Clip()
        harness = NoteTransferHarness(clip)
        harness._handle_note_transfer_command(
            note_transfer_message("duplicate", 7, 3000, [note.note_id])
        )

        self.assertEqual(harness.results, [(7, True, 0, [note.note_id + 1_000_000])])
        self.assertEqual(clip.notes[-1].start_time, 3.0)
        self.assertIs(clip.notes[-1].expression, expression)

        handler_source = ast.get_source_segment(
            SOURCE.read_text(encoding="utf-8"),
            next(
                node for node in tap_class_node().body
                if isinstance(node, ast.FunctionDef) and node.name == "_handle_note_transfer_command"
            ),
        )
        self.assertNotIn("get_all_notes_extended", handler_source)

    def test_loop_multiply_stretches_existing_notes_and_preserves_expression(self):
        expression = object()
        inside = type("Note", (), {
            "note_id": 101,
            "start_time": 1.0,
            "duration": 0.5,
            "expression": expression,
        })()
        outside = type("Note", (), {
            "note_id": 202,
            "start_time": 5.0,
            "duration": 0.25,
            "expression": expression,
        })()

        class Clip:
            is_midi_clip = True
            start_time = 0.0
            start_marker = 0.0
            loop_start = 0.0
            loop_end = 4.0
            end_marker = 4.0
            length = 6.0

            def get_notes_extended(self, *_args):
                return [inside, outside]

            def apply_note_modifications(self, notes):
                self.applied = tuple(notes)

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        track = type("Track", (), {"clip_slots": [slot]})()

        class Harness:
            clip_length_trick = 110.0
            _multiply_loop_by_two = extracted_method("_multiply_loop_by_two")

            def __init__(self):
                self.stretched_automation = None
                self.sent_metadata = False
                self.sent_notes = False

            def song(self):
                return type("Song", (), {"tracks": [track]})()

            def _decoupled_automation_info(self, _clip):
                return None

            def _stretch_clip_automation(self, _clip, source_start, source_length, target_length, **kwargs):
                self.stretched_automation = (
                    source_start,
                    source_length,
                    target_length,
                    kwargs.get("source_decoupled_info"),
                    kwargs.get("target_decoupled_info"),
                )

            def _begin_selected_clip_update_batch(self):
                pass

            def _end_selected_clip_update_batch(self):
                pass

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def _debug_log(self, message):
                raise AssertionError(message)

            def send_selected_clip_metadata(self):
                self.sent_metadata = True

            def send_selected_clip_notes(self):
                self.sent_notes = True

        harness = Harness()
        harness._multiply_loop_by_two(0, 0)

        self.assertEqual((inside.start_time, inside.duration), (2.0, 1.0))
        self.assertEqual((outside.start_time, outside.duration), (5.0, 0.25))
        self.assertEqual(clip.loop_end, 8.0)
        self.assertEqual(clip.end_marker, 8.0)
        self.assertEqual(clip.applied, (inside, outside))
        self.assertIs(inside.expression, expression)
        self.assertEqual(harness.stretched_automation, (0.0, 4.0, 8.0, None, None))
        self.assertTrue(harness.sent_metadata)
        self.assertTrue(harness.sent_notes)

    def test_native_duplicate_loop_invalidates_authored_cache_and_publishes_new_length(self):
        class Clip:
            def __init__(self):
                self.loop_end = 4.0
                self.duplicate_count = 0

            def duplicate_loop(self):
                self.loop_end *= 2.0
                self.duplicate_count += 1

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        track = type("Track", (), {"clip_slots": [slot]})()

        class Harness:
            _duplicate_loop = extracted_method("_duplicate_loop")

            def __init__(self):
                self.cleared = False
                self.sent_metadata = False
                self.sent_notes = False

            def song(self):
                return type("Song", (), {"tracks": [track]})()

            def _decoupled_automation_info(self, _clip):
                return None

            def _clear_authored_automation_steps_for_clip(self, _clip):
                self.cleared = True

            def _begin_selected_clip_update_batch(self):
                pass

            def _end_selected_clip_update_batch(self):
                pass

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def send_selected_clip_metadata(self):
                self.sent_metadata = True

            def send_selected_clip_notes(self):
                self.sent_notes = True

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        harness._duplicate_loop(0, 0)

        self.assertEqual(clip.loop_end, 8.0)
        self.assertEqual(clip.duplicate_count, 1)
        self.assertTrue(harness.cleared)
        self.assertTrue(harness.sent_metadata)
        self.assertTrue(harness.sent_notes)

    def test_decoupled_duplicate_doubles_only_the_logical_note_loop(self):
        previous_info = {
            "note_start": 0.0,
            "note_length": 4.0,
            "physical_length": 16.0,
            "physical_end": 16.0,
            "automation_lengths": {"filter": 16.0},
        }
        doubled_info = dict(previous_info, note_length=8.0, note_end=8.0)

        class Clip:
            loop_start = 0.0
            loop_end = 16.0
            start_marker = 0.0
            end_marker = 16.0

        clip = Clip()

        class Harness:
            _double_decoupled_loop = extracted_method("_double_decoupled_loop")

            def _decoupled_info_with_doubled_note_length(self, _clip, _info):
                return doubled_info

            def _save_decoupled_automation_info_to_name(self, _clip, info):
                self.saved = info

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        result = harness._double_decoupled_loop(clip, previous_info)

        self.assertEqual(result, doubled_info)
        self.assertEqual(harness.saved, doubled_info)
        self.assertEqual((clip.loop_start, clip.loop_end), (0.0, 16.0))
        self.assertEqual((clip.start_marker, clip.end_marker), (0.0, 16.0))

    def test_decoupled_duplicate_grows_shared_loop_when_automation_is_shorter(self):
        notes = [
            type("Note", (), {"note_id": 11, "start_time": 1.0})(),
            type("Note", (), {"note_id": 12, "start_time": 6.0})(),
        ]
        previous_info = {
            "note_start": 0.0,
            "note_length": 8.0,
            "physical_length": 8.0,
            "physical_end": 8.0,
            "automation_lengths": {"filter": 4.0},
        }
        doubled_info = {
            "note_start": 0.0,
            "note_length": 16.0,
            "note_end": 16.0,
            "physical_length": 16.0,
            "physical_end": 16.0,
            "automation_lengths": {"filter": 4.0},
        }

        class Clip:
            loop_start = 0.0
            loop_end = 8.0
            start_marker = 0.0
            end_marker = 8.0

            def get_notes_extended(self, *_args):
                return notes

            def duplicate_notes_by_id(self, note_ids, destination_time):
                self.duplicated = (tuple(note_ids), destination_time)
                return (21, 22)

        clip = Clip()

        class Harness:
            _double_decoupled_loop = extracted_method("_double_decoupled_loop")
            _expand_decoupled_notes_for_duplicate = extracted_method(
                "_expand_decoupled_notes_for_duplicate"
            )

            def _decoupled_info_with_doubled_note_length(self, _clip, _info):
                return doubled_info

            def _rewrite_all_decoupled_automation_envelopes(self, _clip, info):
                self.rewritten = info

            def _save_decoupled_automation_info_to_name(self, _clip, info):
                self.saved = info

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        result = harness._double_decoupled_loop(clip, previous_info)

        self.assertEqual(result, doubled_info)
        self.assertEqual(clip.duplicated, ((11, 12), 9.0))
        self.assertEqual((clip.loop_start, clip.loop_end), (0.0, 16.0))
        self.assertEqual((clip.start_marker, clip.end_marker), (0.0, 16.0))
        self.assertEqual(harness.rewritten, doubled_info)
        self.assertEqual(harness.saved, doubled_info)

    def test_decoupled_duplicate_math_keeps_short_automation_length(self):
        previous_info = {
            "note_start": 0.0,
            "note_length": 8.0,
            "physical_length": 8.0,
            "physical_end": 8.0,
            "automation_lengths": {"filter": 4.0},
        }

        class Harness:
            _decoupled_info_with_doubled_note_length = extracted_method(
                "_decoupled_info_with_doubled_note_length"
            )

            def _clip_automation_parameters(self, _clip, _info):
                return ()

            def _decoupled_automation_max_physical_length(self, _clip, _note_length):
                return 64.0

            def _decoupled_physical_length(self, note_length, automation_lengths, _maximum):
                self.length_inputs = (note_length, tuple(automation_lengths))
                return 16.0

        harness = Harness()
        result = harness._decoupled_info_with_doubled_note_length(
            object(),
            previous_info
        )

        self.assertEqual(result["note_length"], 16.0)
        self.assertEqual(result["automation_lengths"], {"filter": 4.0})
        self.assertEqual(result["physical_length"], 16.0)
        self.assertEqual(harness.length_inputs, (16.0, (4.0,)))

    def test_shared_loop_lcm_handles_automation_shorter_than_notes(self):
        class Harness:
            _decoupled_physical_length = extracted_method(
                "_decoupled_physical_length"
            )

        harness = Harness()
        self.assertEqual(harness._decoupled_physical_length(8.0, (4.0,), 64.0), 8.0)
        self.assertEqual(harness._decoupled_physical_length(16.0, (4.0,), 64.0), 16.0)
        self.assertEqual(harness._decoupled_physical_length(16.0, (8.0,), 64.0), 16.0)

    def test_shared_loop_lcm_handles_three_quarters_and_one_and_a_half(self):
        class Harness:
            _decoupled_physical_length = extracted_method(
                "_decoupled_physical_length"
            )

        harness = Harness()
        # Four-bar notes in 4/4: both 3/4 (12 beats) and 1.5x (24 beats)
        # require a 48-beat shared loop; stretching all lengths needs 96.
        self.assertEqual(harness._decoupled_physical_length(16.0, (12.0,), 256.0), 48.0)
        self.assertEqual(harness._decoupled_physical_length(16.0, (24.0,), 256.0), 48.0)
        self.assertEqual(harness._decoupled_physical_length(32.0, (24.0,), 256.0), 96.0)
        self.assertEqual(harness._decoupled_physical_length(32.0, (48.0,), 256.0), 96.0)

    def test_shared_loop_limit_refuses_inexact_clamping(self):
        class Harness:
            _decoupled_physical_length = extracted_method(
                "_decoupled_physical_length"
            )

        # The exact LCM is 384 beats. Returning the 256-beat cap would not be
        # a shared loop and would silently corrupt the decoupled ratios.
        self.assertIsNone(
            Harness()._decoupled_physical_length(128.0, (192.0,), 256.0)
        )

    def test_decoupled_shared_loop_cap_is_sixty_four_bars(self):
        assignment = next(
            node for node in tap_class_node().body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "DECOUPLED_AUTOMATION_MAX_PHYSICAL_BARS"
                for target in node.targets
            )
        )
        self.assertEqual(ast.literal_eval(assignment.value), 64)

    def test_decoupled_long_press_stretches_notes_automation_and_live_loop(self):
        expression = object()
        first_copy = type("Note", (), {
            "note_id": 101,
            "start_time": 1.0,
            "duration": 0.5,
            "expression": expression,
        })()
        second_copy = type("Note", (), {
            "note_id": 202,
            "start_time": 5.0,
            "duration": 0.5,
            "expression": expression,
        })()
        third_copy = type("Note", (), {
            "note_id": 303,
            "start_time": 9.0,
            "duration": 0.5,
            "expression": expression,
        })()
        previous_info = {
            "note_start": 0.0,
            "note_length": 4.0,
            "physical_length": 16.0,
            "physical_end": 16.0,
            "automation_lengths": {"filter": 16.0},
        }
        doubled_info = {
            "note_start": 0.0,
            "note_length": 8.0,
            "note_end": 8.0,
            "physical_length": 32.0,
            "physical_end": 32.0,
            "automation_lengths": {"filter": 32.0},
        }

        class Clip:
            is_midi_clip = True
            start_time = 0.0
            start_marker = 0.0
            loop_start = 0.0
            length = 16.0

            def __init__(self):
                self._loop_end = 16.0
                self._end_marker = 16.0

            @property
            def loop_end(self):
                return self._loop_end

            @loop_end.setter
            def loop_end(self, value):
                if value > self._end_marker:
                    raise AssertionError("loop_end was extended before end_marker")
                self._loop_end = value

            @property
            def end_marker(self):
                return self._end_marker

            @end_marker.setter
            def end_marker(self, value):
                self._end_marker = value

            def get_notes_extended(self, *_args):
                return [first_copy, second_copy, third_copy]

            def apply_note_modifications(self, notes):
                self.applied = tuple(notes)

        clip = Clip()
        slot = type("Slot", (), {"has_clip": True, "clip": clip})()
        track = type("Track", (), {"clip_slots": [slot]})()

        class Harness:
            clip_length_trick = 110.0
            _multiply_loop_by_two = extracted_method("_multiply_loop_by_two")

            def __init__(self):
                self.stretched_automation = None

            def song(self):
                return type("Song", (), {"tracks": [track]})()

            def _decoupled_automation_info(self, _clip):
                return previous_info

            def _decoupled_info_with_stretched_lengths(self, _clip, _info, factor):
                self.asserted_factor = factor
                return doubled_info

            def _stretch_clip_automation(self, _clip, source_start, source_length, target_length, **kwargs):
                self.stretched_automation = (
                    source_start,
                    source_length,
                    target_length,
                    kwargs.get("source_decoupled_info"),
                    kwargs.get("target_decoupled_info"),
                )

            def _save_decoupled_automation_info_to_name(self, _clip, info):
                self.saved = info

            def _begin_selected_clip_update_batch(self):
                pass

            def _end_selected_clip_update_batch(self):
                pass

            def _begin_undo_step(self):
                return True

            def _end_undo_step(self, _started):
                pass

            def send_selected_clip_metadata(self):
                self.sent_metadata = True

            def send_selected_clip_notes(self):
                self.sent_notes = True

            def _debug_log(self, message):
                raise AssertionError(message)

        harness = Harness()
        harness._multiply_loop_by_two(0, 0)

        self.assertEqual((first_copy.start_time, first_copy.duration), (2.0, 1.0))
        self.assertEqual((second_copy.start_time, second_copy.duration), (10.0, 1.0))
        self.assertEqual((third_copy.start_time, third_copy.duration), (18.0, 1.0))
        self.assertEqual(clip.applied, (first_copy, second_copy, third_copy))
        self.assertIs(first_copy.expression, expression)
        self.assertEqual(harness.asserted_factor, 2.0)
        self.assertEqual(harness.saved["note_length"], 8.0)
        self.assertEqual(harness.saved["automation_lengths"], {"filter": 32.0})
        self.assertEqual(harness.saved["physical_length"], 32.0)
        self.assertEqual((clip.loop_start, clip.loop_end), (0.0, 32.0))
        self.assertEqual((clip.start_marker, clip.end_marker), (0.0, 32.0))
        self.assertEqual(
            harness.stretched_automation,
            (0.0, 16.0, 32.0, previous_info, doubled_info)
        )
        self.assertTrue(harness.sent_metadata)
        self.assertTrue(harness.sent_notes)

    def test_decoupled_stretch_doubles_each_logical_and_physical_length(self):
        previous_info = {
            "note_start": 2.0,
            "note_length": 3.0,
            "physical_length": 12.0,
            "physical_end": 14.0,
            "automation_lengths": {"filter": 4.0, "send": 6.0},
        }

        class Harness:
            _decoupled_info_with_stretched_lengths = extracted_method(
                "_decoupled_info_with_stretched_lengths"
            )

            def _decoupled_automation_max_physical_length(self, _clip, _note_length):
                return 96.0

            def _decoupled_physical_length(self, note_length, automation_lengths, _maximum):
                self.received_lengths = (note_length, tuple(sorted(automation_lengths)))
                return 24.0

        harness = Harness()
        result = harness._decoupled_info_with_stretched_lengths(object(), previous_info, 2.0)

        self.assertEqual(result["note_start"], 2.0)
        self.assertEqual(result["note_length"], 6.0)
        self.assertEqual(result["automation_lengths"], {"filter": 8.0, "send": 12.0})
        self.assertEqual(result["physical_length"], 24.0)
        self.assertEqual(result["physical_end"], 26.0)
        self.assertEqual(harness.received_lengths, (6.0, (8.0, 12.0)))

    def test_decoupled_stretch_preserves_fractional_loop_ratios(self):
        class Harness:
            _decoupled_info_with_stretched_lengths = extracted_method(
                "_decoupled_info_with_stretched_lengths"
            )
            _decoupled_physical_length = extracted_method(
                "_decoupled_physical_length"
            )

            def _decoupled_automation_max_physical_length(self, _clip, _note_length):
                return 256.0

        harness = Harness()
        for automation_length in (12.0, 24.0):
            source = {
                "note_start": 0.0,
                "note_length": 16.0,
                "physical_length": 48.0,
                "physical_end": 48.0,
                "automation_lengths": {"filter": automation_length},
            }
            result = harness._decoupled_info_with_stretched_lengths(
                object(), source, 2.0
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["note_length"], 32.0)
            self.assertEqual(
                result["automation_lengths"],
                {"filter": automation_length * 2.0}
            )
            self.assertEqual(result["physical_length"], 96.0)

    def test_automation_stretch_scales_time_duration_and_preserves_identity(self):
        class Harness:
            _scaled_automation_steps = extracted_method("_scaled_automation_steps")

            def _automation_sorted_steps(self, steps):
                return tuple(sorted(steps, key=lambda step: step[0]))

            def _automation_step_tuple(self, step, _index):
                return step

        steps = (
            (2.5, 0.25, 0.2, -0.4, 41, 7),
            (4.0, 0.5, 0.8, 0.6, 42, 8),
        )
        result = Harness()._scaled_automation_steps(steps, 2.0, 2.0)

        self.assertEqual(result, (
            (3.0, 0.5, 0.2, -0.4, 41, 7),
            (6.0, 1.0, 0.8, 0.6, 42, 8),
        ))

        exact_steps = (
            (2.5, 0.25, 0.2, 0.0, 41, 7, True, 0.12, 0.34, 0.78, 0.91),
            (4.0, 0.5, 0.8, 0.0, 42, 8, True, 0.5, 0.5, 0.5, 0.5),
        )
        self.assertEqual(
            Harness()._scaled_automation_steps(exact_steps, 2.0, 2.0),
            (
                (3.0, 0.5, 0.2, 0.0, 41, 7, True, 0.12, 0.34, 0.78, 0.91),
                (6.0, 1.0, 0.8, 0.0, 42, 8, True, 0.5, 0.5, 0.5, 0.5),
            )
        )

    def test_track_input_state_codes_include_audio_arm_state(self):
        class Harness:
            _track_input_state_codes = extracted_method("_track_input_state_codes")

        def track(has_audio, armed, grouped=False, group=False):
            slots = [type("Slot", (), {"is_group_slot": group})()]
            return type("Track", (), {
                "has_audio_input": has_audio,
                "arm": armed,
                "is_grouped": grouped,
                "clip_slots": slots,
            })()

        states = Harness()._track_input_state_codes([
            track(False, False),
            track(True, False),
            track(True, True),
            track(True, True, grouped=True),
            track(False, False, group=True),
        ])
        self.assertEqual(states, ["0", "1", "5", "6", "2"])

    def test_cut_paste_moves_original_note_ids_and_expression(self):
        expression = object()
        notes = [
            type("Note", (), {"note_id": 11, "start_time": 1.0, "expression": expression})(),
            type("Note", (), {"note_id": 22, "start_time": 1.5, "expression": expression})(),
        ]

        class Clip:
            is_midi_clip = True
            start_time = 0.0
            start_marker = 0.0
            loop_start = 0.0
            loop_end = 8.0
            end_marker = 8.0
            length = 8.0

            def get_notes_by_id(self, note_ids):
                return tuple(item for item in notes if item.note_id in note_ids)

            def get_notes_extended(self, *_args):
                return tuple(notes)

            def apply_note_modifications(self, modified):
                self.applied = tuple(modified)

        clip = Clip()
        harness = NoteTransferHarness(clip)
        harness._handle_note_transfer_command(
            note_transfer_message("move", 8, 4000, [11, 22])
        )

        self.assertEqual(harness.results, [(8, True, 0, [11, 22])])
        self.assertEqual([item.start_time for item in clip.applied], [4.0, 4.5])
        self.assertTrue(all(item.expression is expression for item in clip.applied))

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
        transfer_source = ast.get_source_segment(
            source,
            next(
                node for node in tap_class_node().body
                if isinstance(node, ast.FunctionDef) and node.name == "_handle_note_transfer_command"
            ),
        )
        self.assertNotIn("scene_metadata", transfer_source)

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

    def test_post_write_does_not_reenable_already_enabled_automation(self):
        class Parameter:
            automation_state = 1

        class Harness:
            _re_enable_after_automation_write = extracted_method(
                "_re_enable_after_automation_write"
            )
            _parameter_automation_is_enabled = extracted_method(
                "_parameter_automation_is_enabled"
            )

            def __init__(self):
                self.reenable_calls = 0
                self.scheduled = []
                self.enabled_updates = 0

            def _re_enable_parameter_automation(self, _parameter):
                self.reenable_calls += 1

            def _re_enable_written_automation_if_needed(self, _parameter):
                raise AssertionError("enabled automation needs no retry")

            def _send_re_enable_automation_enabled(self, force=False):
                if force:
                    self.enabled_updates += 1

            def schedule_message(self, ticks, callback):
                self.scheduled.append((ticks, callback))

            def _debug_log(self, _message):
                pass

        harness = Harness()
        harness._re_enable_after_automation_write(Parameter(), True)

        self.assertEqual(harness.reenable_calls, 0)
        self.assertEqual(harness.scheduled, [])
        self.assertEqual(harness.enabled_updates, 1)

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
