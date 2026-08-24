from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Final


class InventoryFaultMode(str, Enum):
    NONE = "none"
    HIGH_LATENCY = "high_latency"
    API_TIMEOUT = "api_timeout"
    DATABASE_FAILURE = "database_failure"


@dataclass(frozen=True)
class FaultProfile:
    delay_seconds: float = 0.0


FAULT_PROFILES: Final[dict[InventoryFaultMode, FaultProfile]] = {
    InventoryFaultMode.NONE: FaultProfile(),
    InventoryFaultMode.HIGH_LATENCY: FaultProfile(delay_seconds=0.5),
    InventoryFaultMode.API_TIMEOUT: FaultProfile(delay_seconds=1.5),
    InventoryFaultMode.DATABASE_FAILURE: FaultProfile(),
}


@dataclass(frozen=True)
class FaultSnapshot:
    mode: InventoryFaultMode
    delay_seconds: float
    changed_at: datetime


class SimulatedDatastoreFailure(RuntimeError):
    """Raised at the demo-only inventory data-access boundary."""


class FaultController:
    """Stores one safe, process-local fault mode for the inventory service."""

    def __init__(self) -> None:
        self._mode = InventoryFaultMode.NONE
        self._changed_at = self._utc_now()
        self._lock = RLock()

    def snapshot(self) -> FaultSnapshot:
        with self._lock:
            return self._snapshot_unlocked()

    def set_mode(self, mode: InventoryFaultMode) -> FaultSnapshot:
        with self._lock:
            self._mode = mode
            self._changed_at = self._utc_now()
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> FaultSnapshot:
        profile = FAULT_PROFILES[self._mode]

        return FaultSnapshot(
            mode=self._mode,
            delay_seconds=profile.delay_seconds,
            changed_at=self._changed_at,
        )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)
