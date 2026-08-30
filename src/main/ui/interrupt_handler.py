from __future__ import annotations

class DoubleEscapeDetector:
    def __init__(self) -> None:
        self._waiting_for_second = False

    def press(self) -> bool:
        if self._waiting_for_second:
            self._waiting_for_second = False
            return True
        self._waiting_for_second = True
        return False

    def reset(self) -> None:
        self._waiting_for_second = False
