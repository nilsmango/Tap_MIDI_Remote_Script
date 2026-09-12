from __future__ import absolute_import, print_function, unicode_literals


class AutomationEvent(tuple):
    """Canonical tuple-compatible automation event used on both paths."""

    __slots__ = ()
    _fields = (
        "time", "duration", "value", "curve", "event_id", "order",
        "uses_exact_controls", "control_x1", "control_y1", "control_x2",
        "control_y2",
    )

    def __new__(
            cls, time_value, duration, value, curve, event_id, order,
            uses_exact_controls=False, control_x1=0.5, control_y1=0.5,
            control_x2=0.5, control_y2=0.5):
        values = (
            float(time_value), float(duration), float(value), float(curve),
            int(event_id), int(order),
        )
        if uses_exact_controls:
            values += (
                True, float(control_x1), float(control_y1),
                float(control_x2), float(control_y2),
            )
        return tuple.__new__(cls, values)

    def __getattr__(self, name):
        try:
            index = self._fields.index(name)
        except ValueError:
            raise AttributeError(name)
        if index >= len(self):
            if name == "uses_exact_controls":
                return False
            if name.startswith("control_"):
                return 0.5
            raise AttributeError(name)
        return self[index]


class AutomationTargetContext(dict):
    """Typed mapping for one validated clip/parameter/revision snapshot."""


class AutomationContextRegistry(dict):
    def __init__(self, contexts=None, counter=0):
        dict.__init__(self, contexts or {})
        self.counter = int(counter)

    def create(self):
        self.counter = 1 if self.counter >= 0x7FFFFFFF else self.counter + 1
        token = "{:08X}".format(self.counter)
        context = AutomationTargetContext(token=token)
        self[token] = context
        return context

    def expire(self, now, maximum_age):
        for token in tuple(self.keys()):
            if now - float(self[token].get("last_activity", 0.0)) > maximum_age:
                self.pop(token, None)

    def trim(self, maximum_count):
        while len(self) > maximum_count:
            oldest_token = min(
                self,
                key=lambda token: float(self[token].get("last_activity", 0.0))
            )
            self.pop(oldest_token, None)


class AutomationUndoLease(object):
    """Idempotent ownership of one Live undo step."""

    def __init__(self, attempted=False, started=False):
        self.attempted = bool(attempted)
        self.started = bool(started)

    def begin(self, owner):
        if not self.attempted:
            self.attempted = True
            self.started = bool(owner._begin_undo_step())
        return self.started

    def close(self, owner):
        started = self.started
        self.started = False
        self.attempted = False
        if started:
            owner._end_undo_step(True)


class AutomationPencilTransaction(dict):
    phase = "streaming"

    def __init__(self, values):
        dict.__init__(self, values)
        self.undo_lease = AutomationUndoLease(
            values.get("undo_step_attempted", False),
            values.get("undo_step_started", False),
        )

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if key == "undo_step_attempted":
            self.undo_lease.attempted = bool(value)
        elif key == "undo_step_started":
            self.undo_lease.started = bool(value)


class ExactAutomationWriteMode(object):
    STREAMED_TWO_PASS = "streamedTwoPass"
    BATCHED_FULL = "batchedFull"


class ExactAutomationWritePhase(object):
    WRITING = "writing"
    VERIFYING = "verifying"
    SETTLING = "settling"
    COMPLETED = "completed"
    FAILED = "failed"


class ExactAutomationWriteTransaction(dict):
    def __init__(self, mode, values):
        dict.__init__(self, values)
        self.mode = mode
        self.phase = ExactAutomationWritePhase.WRITING
        self.undo_lease = AutomationUndoLease(
            values.get("undo_step_attempted", False),
            values.get("undo_step_started", False),
        )

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if key == "undo_step_attempted":
            self.undo_lease.attempted = bool(value)
        elif key == "undo_step_started":
            self.undo_lease.started = bool(value)


class LiveAutomationWriter(object):
    """Phase owner; the two established cadence algorithms remain separate."""

    def __init__(self):
        self.transaction = None

    def begin(self, transaction):
        self.transaction = transaction
        return transaction

    def finish(self, transaction, failed=False):
        if transaction is not None:
            transaction.phase = (
                ExactAutomationWritePhase.FAILED
                if failed else ExactAutomationWritePhase.COMPLETED
            )
        if self.transaction is transaction:
            self.transaction = None


class AutomationTransferCoordinator(object):
    def __init__(self):
        self.contexts = AutomationContextRegistry()
        self.pencil = None
        self.writer = LiveAutomationWriter()

