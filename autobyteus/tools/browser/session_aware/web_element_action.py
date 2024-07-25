from enum import Enum, auto

class WebElementAction(Enum):
    CLICK = auto()
    TYPE = auto()
    SELECT = auto()
    CHECK = auto()
    SUBMIT = auto()
    HOVER = auto()
    DOUBLE_CLICK = auto()

    def __str__(self):
        return self.name.lower()

    @staticmethod
    def from_string(action_string):
        try:
            return WebElementAction[action_string.upper()]
        except KeyError:
            raise ValueError(f"Unsupported action: {action_string}")