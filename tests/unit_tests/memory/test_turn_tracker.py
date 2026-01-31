from autobyteus.memory.turn_tracker import TurnTracker


def test_turn_tracker_starts_at_one_by_default():
    tracker = TurnTracker()
    assert tracker.next_turn_id() == "turn_0001"


def test_turn_tracker_increments():
    tracker = TurnTracker(start=3)
    assert tracker.next_turn_id() == "turn_0003"
    assert tracker.next_turn_id() == "turn_0004"
