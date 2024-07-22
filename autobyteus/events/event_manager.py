class EventManager:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event, listener):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(listener)

    def unsubscribe(self, event, listener):
        if event in self.listeners:
            self.listeners[event].remove(listener)

    def emit(self, event, *args, **kwargs):
        if event in self.listeners:
            for listener in self.listeners[event]:
                listener(*args, **kwargs)