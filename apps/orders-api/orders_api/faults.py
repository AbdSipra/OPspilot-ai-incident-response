from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import RLock


class OrdersFaultMode(str, Enum):
    NONE = "none"
    BAD_CONFIGURATION = "bad_configuration"


@dataclass(frozen=True)
class FaultSnapshot:
    mode: OrdersFaultMode
    changed_at: datetime


class OrdersFaultController:
    """Stores one safe, process-local fault mode for the orders service."""

    def __init__(self) -> None:
        self._mode = OrdersFaultMode.NONE
        self._changed_at = self._utc_now()
        self._lock = RLock()

    def snapshot(self) -> FaultSnapshot:
        with self._lock:
            return FaultSnapshot(
                mode=self._mode,
                changed_at=self._changed_at,
            )

    def set_mode(self, mode: OrdersFaultMode) -> FaultSnapshot:
        with self._lock:
            self._mode = mode
            self._changed_at = self._utc_now()
            return FaultSnapshot(
                mode=self._mode,
                changed_at=self._changed_at,
            )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)
