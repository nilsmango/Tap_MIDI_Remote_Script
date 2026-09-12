from __future__ import absolute_import, print_function, unicode_literals

import math
import time

PERFORMANCE_DIAGNOSTICS_ENABLED = False

class TapScheduledCall:
    """Cancellable adapter for ControlSurface.schedule_message."""

    TICKS_PER_SECOND = 10.0

    def __init__(self, surface, delay_seconds, callback, args=()):
        self._active = True
        self._callback = callback
        self._args = tuple(args)
        delay_ticks = max(1, int(math.ceil(max(0.0, delay_seconds) * self.TICKS_PER_SECOND)))
        surface.schedule_message(delay_ticks, self._run)

    def _run(self):
        if not self._active:
            return
        self._active = False
        self._callback(*self._args)

    def cancel(self):
        self._active = False

    def is_alive(self):
        return self._active


class TapPerformanceDiagnostics:
    """Debug-only aggregate timings and counters for repeatable baselines."""

    SUMMARY_INTERVAL_SECONDS = 30.0

    def __init__(self, enabled=None, clock=None, emit=None):
        self.enabled = (
            PERFORMANCE_DIAGNOSTICS_ENABLED
            if enabled is None else bool(enabled)
        )
        self._clock = clock or time.monotonic
        self._emit = emit or (lambda _message: None)
        self._last_summary_at = self._clock() if self.enabled else 0.0
        self._operation_stats = {}
        self._traversal_counts = {}
        self._incoming_sysex_packets = {}
        self._incoming_sysex_bytes = {}
        self._outgoing_sysex_packets = {}
        self._outgoing_sysex_bytes = {}
        self._selected_clip_notes_calls = 0
        self._selected_clip_notes_get_duration = 0.0
        self._selected_clip_notes_get_max_duration = 0.0
        self._selected_clip_notes_fetched = 0
        self._selected_clip_notes_payload_bytes = 0
        self._selected_clip_notes_chunks = 0
        self._selected_clip_notes_suppressions = 0
        self._selected_clip_metadata_calls = 0
        self._selected_clip_metadata_payload_bytes = 0
        self._selected_clip_metadata_chunks = 0
        self._selected_clip_metadata_coalesced = 0
        self._listener_totals = {}

    def start_operation(self):
        if not self.enabled:
            return None
        return self._clock()

    def finish_operation(self, name, started_at):
        if not self.enabled or started_at is None:
            return 0.0
        duration = max(0.0, self._clock() - started_at)
        stats = self._operation_stats.setdefault(name, [0, 0.0, 0.0])
        stats[0] += 1
        stats[1] += duration
        stats[2] = max(stats[2], duration)
        return duration

    def record_traversal(self, kind, count):
        if not self.enabled or count <= 0:
            return
        self._traversal_counts[kind] = self._traversal_counts.get(kind, 0) + int(count)

    def record_incoming_sysex(self, manufacturer_id, byte_count):
        if not self.enabled:
            return
        key = str(manufacturer_id)
        self._incoming_sysex_packets[key] = self._incoming_sysex_packets.get(key, 0) + 1
        self._incoming_sysex_bytes[key] = self._incoming_sysex_bytes.get(key, 0) + max(0, int(byte_count))

    def record_outgoing_sysex(self, message):
        if not self.enabled or len(message) < 2:
            return
        key = str(message[1])
        self._outgoing_sysex_packets[key] = self._outgoing_sysex_packets.get(key, 0) + 1
        self._outgoing_sysex_bytes[key] = self._outgoing_sysex_bytes.get(key, 0) + len(message)

    def record_selected_clip_notes_call(self):
        if self.enabled:
            self._selected_clip_notes_calls += 1

    def record_selected_clip_notes_fetch(self, duration, note_count):
        if not self.enabled:
            return
        duration = max(0.0, duration)
        self._selected_clip_notes_get_duration += duration
        self._selected_clip_notes_get_max_duration = max(
            self._selected_clip_notes_get_max_duration,
            duration,
        )
        self._selected_clip_notes_fetched += max(0, int(note_count))

    def record_selected_clip_notes_payload(self, payload_bytes, chunks):
        if not self.enabled:
            return
        self._selected_clip_notes_payload_bytes += max(0, int(payload_bytes))
        self._selected_clip_notes_chunks += max(0, int(chunks))

    def record_selected_clip_notes_suppression(self):
        if self.enabled:
            self._selected_clip_notes_suppressions += 1

    def record_selected_clip_metadata_call(self):
        if self.enabled:
            self._selected_clip_metadata_calls += 1

    def record_selected_clip_metadata_payload(self, payload_bytes, chunks):
        if not self.enabled:
            return
        self._selected_clip_metadata_payload_bytes += max(0, int(payload_bytes))
        self._selected_clip_metadata_chunks += max(0, int(chunks))

    def record_selected_clip_metadata_coalesced(self):
        if self.enabled:
            self._selected_clip_metadata_coalesced += 1

    def record_listener_binding(self, feature, delta):
        if not self.enabled:
            return
        current = self._listener_totals.get(feature, 0)
        self._listener_totals[feature] = max(0, current + int(delta))

    def set_listener_total(self, feature, count):
        if self.enabled:
            self._listener_totals[feature] = max(0, int(count))

    def snapshot(self):
        if not self.enabled:
            return {"enabled": False}
        return {
            "enabled": True,
            "operations": {
                name: tuple(values)
                for name, values in self._operation_stats.items()
            },
            "traversals": dict(self._traversal_counts),
            "incoming_sysex_packets": dict(self._incoming_sysex_packets),
            "incoming_sysex_bytes": dict(self._incoming_sysex_bytes),
            "outgoing_sysex_packets": dict(self._outgoing_sysex_packets),
            "outgoing_sysex_bytes": dict(self._outgoing_sysex_bytes),
            "selected_clip_notes_calls": self._selected_clip_notes_calls,
            "selected_clip_notes_get_duration": self._selected_clip_notes_get_duration,
            "selected_clip_notes_get_max_duration": self._selected_clip_notes_get_max_duration,
            "selected_clip_notes_fetched": self._selected_clip_notes_fetched,
            "selected_clip_notes_payload_bytes": self._selected_clip_notes_payload_bytes,
            "selected_clip_notes_chunks": self._selected_clip_notes_chunks,
            "selected_clip_notes_suppressions": self._selected_clip_notes_suppressions,
            "selected_clip_metadata_calls": self._selected_clip_metadata_calls,
            "selected_clip_metadata_payload_bytes": self._selected_clip_metadata_payload_bytes,
            "selected_clip_metadata_chunks": self._selected_clip_metadata_chunks,
            "selected_clip_metadata_coalesced": self._selected_clip_metadata_coalesced,
            "listener_totals": dict(self._listener_totals),
        }

    @staticmethod
    def _compact_mapping(values):
        return ",".join(
            "{}={}".format(key, values[key])
            for key in sorted(values)
        ) or "-"

    @staticmethod
    def _milliseconds(value):
        return "{:.2f}".format(value * 1000.0)

    def summary_line(self, reason="on-demand"):
        if not self.enabled:
            return "TapPerf disabled"
        periodic = self._operation_stats.get("periodic", (0, 0.0, 0.0))
        operations = ";".join(
            "{}:{}:{}/{}".format(
                name,
                values[0],
                self._milliseconds(values[1]),
                self._milliseconds(values[2]),
            )
            for name, values in sorted(self._operation_stats.items())
        ) or "-"
        return (
            "TapPerf reason={} periodic={}:{}/{}ms ops={} "
            "traversals={} inSysEx={} inBytes={} outSysEx={} outBytes={} "
            "notes={}:{}ms/{}ms fetched={} payload={} chunks={} suppressed={} "
            "metadata={} bytes={} chunks={} coalesced={} listeners={}"
        ).format(
            reason,
            periodic[0],
            self._milliseconds(periodic[1]),
            self._milliseconds(periodic[2]),
            operations,
            self._compact_mapping(self._traversal_counts),
            self._compact_mapping(self._incoming_sysex_packets),
            self._compact_mapping(self._incoming_sysex_bytes),
            self._compact_mapping(self._outgoing_sysex_packets),
            self._compact_mapping(self._outgoing_sysex_bytes),
            self._selected_clip_notes_calls,
            self._milliseconds(self._selected_clip_notes_get_duration),
            self._milliseconds(self._selected_clip_notes_get_max_duration),
            self._selected_clip_notes_fetched,
            self._selected_clip_notes_payload_bytes,
            self._selected_clip_notes_chunks,
            self._selected_clip_notes_suppressions,
            self._selected_clip_metadata_calls,
            self._selected_clip_metadata_payload_bytes,
            self._selected_clip_metadata_chunks,
            self._selected_clip_metadata_coalesced,
            self._compact_mapping(self._listener_totals),
        )

    def emit_summary(self, reason="on-demand"):
        if not self.enabled:
            return None
        message = self.summary_line(reason)
        self._emit(message)
        return message

    def maybe_emit_summary(self):
        if not self.enabled:
            return
        now = self._clock()
        if now - self._last_summary_at >= self.SUMMARY_INTERVAL_SECONDS:
            self._last_summary_at = now
            self.emit_summary("periodic")

