"""Read-only snapshot transitions. No Pygame, gameplay or transport dependency.

Returned events describe presentation work, never gameplay commands. Snapshots
can skip transitions, so this observer cannot guarantee every interaction cue.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class AudioEvent:
    """A one-shot cue or a processing-loop lifecycle instruction."""

    action: Literal["play", "start_loop", "stop_loop", "stop_all_loops"]
    cue: str | None = None
    station_id: str | None = None


@dataclass(frozen=True)
class _Item:
    kind: str
    patient: int
    test: str | None


@dataclass(frozen=True)
class _Station:
    phase: str
    patient: int


@dataclass(frozen=True)
class _Snapshot:
    patient: int
    started: bool
    finished: bool
    connected: bool
    items: tuple[_Item | None, ...]
    stations: tuple[tuple[str, _Station], ...]
    reports: frozenset[str]

    @classmethod
    def capture(cls, state: Mapping[str, Any]) -> "_Snapshot":
        # Copy individual primitive values: host snapshots share mutable items,
        # lists and station dictionaries with the live simulation.
        items = []
        for player in state["players"]:
            item = player["item"]
            items.append(None if item is None else _Item(
                str(item["kind"]), int(item["patient"]),
                str(item["test"]) if item.get("test") is not None else None))
        return cls(
            int(state["patient"]), bool(state["started"]),
            bool(state["finished"]), bool(state["connected"]), tuple(items),
            tuple(sorted((str(key), _Station(str(value["phase"]), int(value["patient"])))
                         for key, value in state["stations"].items())),
            frozenset(str(test) for test in state["package_reports"]))

    @property
    def active(self) -> bool:
        return self.started and self.connected and not self.finished


class AudioObserver:
    """Compare confirmed snapshots and return immutable audio events.

    Use one instance per local game session. Call reset() for a new session or
    pass a stable session_id to observe(). Call disconnect() when the transport
    disconnects even if its last snapshot still says connected=True.
    """

    def __init__(self) -> None:
        self._previous: _Snapshot | None = None
        self._session_id: str | int | None = None
        self._loops: set[str] = set()
        self._result_played = False

    def _stop_loops(self) -> tuple[AudioEvent, ...]:
        if not self._loops:
            return ()
        self._loops.clear()
        return (AudioEvent("stop_all_loops"),)

    def reset(self) -> tuple[AudioEvent, ...]:
        """Stop loops and forget the session, including its result cue latch."""
        events = self._stop_loops()
        self._previous = None
        self._session_id = None
        self._result_played = False
        return events

    def disconnect(self) -> tuple[AudioEvent, ...]:
        """Stop loops and baseline on reconnect; preserve result deduplication."""
        events = self._stop_loops()
        self._previous = None
        return events

    def present_result(self, result: Literal["success", "failure"]) -> tuple[AudioEvent, ...]:
        """Play the externally selected result once per session, never score it.

        Repeated or contradictory results are ignored after the first valid
        result. Unknown values are silent and do not consume the result latch.
        """
        if result not in ("success", "failure") or self._result_played:
            return ()
        self._result_played = True
        return self._stop_loops() + (AudioEvent("play", f"round_{result}"),)

    def observe(
        self, state: Mapping[str, Any], *, session_id: str | int | None = None,
    ) -> tuple[AudioEvent, ...]:
        """Read the current main.py snapshot schema without retaining references.

        The first snapshot, reconnect, patient change and session change are
        silent baselines (apart from stopping previously requested loops).
        Baseline processing stations do not start a loop retroactively.
        """
        current = _Snapshot.capture(state)
        events: list[AudioEvent] = []
        if session_id != self._session_id:
            events.extend(self.reset())
        self._session_id = session_id
        previous, self._previous = self._previous, current
        if previous is None:
            return tuple(events)

        # A new round can also be visible without an explicit session token.
        if (previous.finished and not current.finished) or (previous.started and not current.started):
            self._result_played = False
            return tuple(events) + self._stop_loops()
        if current.patient != previous.patient:
            return tuple(events) + self._stop_loops()
        if not current.active or not previous.active or self._result_played:
            return tuple(events) + self._stop_loops()

        before, after = dict(previous.stations), dict(current.stations)
        acquired = {index: item for index, (old, item) in enumerate(zip(previous.items, current.items))
                    if old is None and item is not None}
        collected: set[int] = set()

        # Stop loops on any observed exit, including removed/reset stations.
        for station_id in sorted(self._loops.copy()):
            if (station_id not in after or after[station_id].phase != "processing"
                    or before.get(station_id) != after[station_id]):
                self._loops.remove(station_id)
                events.append(AudioEvent("stop_loop", station_id=station_id))

        for station_id, station in current.stations:
            old = before.get(station_id)
            if old is None:
                continue
            if old.phase == "idle" and station.phase == "processing":
                events.extend((AudioEvent("play", "machine_insert", station_id),
                               AudioEvent("play", "processing_start", station_id),
                               AudioEvent("start_loop", "processing_loop", station_id)))
                self._loops.add(station_id)
            elif (old.phase == "processing" and station.phase == "output"
                  and old.patient == station.patient):
                events.append(AudioEvent("play", "processing_complete", station_id))
            elif old.phase == "output" and station.phase == "idle":
                matching = [index for index, item in acquired.items()
                            if item.kind == "report" and item.test == station_id
                            and item.patient == old.patient]
                if matching:
                    events.append(AudioEvent("play", "machine_remove", station_id))
                    collected.update(matching)

        # A collected machine report gets its specific cue, not two one-shots.
        events.extend(AudioEvent("play", "pickup") for index in acquired if index not in collected)
        if current.reports - previous.reports:
            # Coalesce additions in one snapshot to avoid stacked identical SFX.
            events.append(AudioEvent("play", "package_insert", "package"))
        return tuple(events)
