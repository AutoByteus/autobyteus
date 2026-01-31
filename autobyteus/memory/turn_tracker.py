class TurnTracker:
    def __init__(self, start: int = 1):
        if start < 1:
            raise ValueError("start must be >= 1")
        self._counter = start - 1

    def next_turn_id(self) -> str:
        self._counter += 1
        return f"turn_{self._counter:04d}"
