"""Immutable display snapshots, not gameplay models or authoritative state.

A/B can adapt authoritative data into these values without importing the demo.
Progress and completion are supplied by the caller; rendering never advances them.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PatientView:
    patient_id: str
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class PlayerView:
    player_id: str
    x: int
    y: int
    held_item: str | None = None


@dataclass(frozen=True)
class SampleView:
    sample_id: str
    x: int
    y: int


@dataclass(frozen=True)
class StationView:
    station_id: str
    station_type: str
    label: tuple[str, ...]
    x: int
    y: int
    width: int = 210
    is_processing: bool = False
    processing_progress: float = 0.0
    is_complete: bool = False


@dataclass(frozen=True)
class RoundView:
    time_remaining: float
    patients: tuple[PatientView, ...]
    stations: tuple[StationView, ...]
    players: tuple[PlayerView, ...]
    samples: tuple[SampleView, ...]
