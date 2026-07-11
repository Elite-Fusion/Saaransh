"""
Monotonic latency timer.

A tiny stdlib-only helper so the provider layer can measure request
duration without depending on any third-party package. ``time.monotonic``
is the right clock for measuring elapsed time (it never goes backwards
even if the system clock is adjusted).

Usage::

    timer = LatencyTimer()
    timer.start()
    ...   # do work
    print(timer.elapsed_ms())
"""
from __future__ import annotations

import time
from typing import Any


class LatencyTimer:
    """A reusable monotonic latency timer.

    The timer is created in a stopped state. Call :meth:`start` to begin
    a measurement, :meth:`elapsed_ms` to read the elapsed time at any
    later point (including while still running), and :meth:`stop` to
    freeze the final value. Calling :meth:`start` again resets the
    measurement.
    """

    __slots__ = ("_start", "_stop")

    def __init__(self) -> None:
        self._start: float | None = None
        self._stop: float | None = None

    def start(self) -> "LatencyTimer":
        """Begin (or restart) the measurement. Returns ``self``."""
        self._start = time.monotonic()
        self._stop = None
        return self

    def stop(self) -> "LatencyTimer":
        """Freeze the current value. Subsequent ``elapsed_ms`` calls
        return the same number until :meth:`start` is called again."""
        if self._start is None:
            raise RuntimeError("LatencyTimer.stop() called before start()")
        if self._stop is None:
            self._stop = time.monotonic()
        return self

    def elapsed_ms(self) -> int:
        """Return the elapsed time in whole milliseconds.

        Rounded to the nearest integer. If the timer has been stopped,
        the value is frozen; otherwise it reflects the time since
        :meth:`start`.
        """
        if self._start is None:
            raise RuntimeError("LatencyTimer.elapsed_ms() called before start()")
        end = self._stop if self._stop is not None else time.monotonic()
        return int(round((end - self._start) * 1000))

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the ``ChatResponse.metadata`` payload.

        The keys here match the logging convention used by
        :class:`backend.ai.providers.base.AIProvider` and
        :class:`backend.ai.services.chat_service.ChatService`.
        """
        return {"latency_ms": self.elapsed_ms()}

    def __repr__(self) -> str:  # pragma: no cover
        state = "stopped" if self._stop is not None else "running"
        return f"<LatencyTimer {state} elapsed_ms={self.elapsed_ms() if self._start else 0}>"
