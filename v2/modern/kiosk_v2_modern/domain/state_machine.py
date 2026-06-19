# -*- coding: utf-8 -*-


class InvalidTransition(ValueError):
    pass


class TransitionResult(object):
    def __init__(self, from_state, event, to_state, effects):
        self.from_state = from_state
        self.event = event
        self.to_state = to_state
        self.effects = tuple(effects)


class StateMachine(object):
    def __init__(self, contract):
        self.state = contract["initialState"]
        self._transitions = {}
        for item in contract["transitions"]:
            key = (item["from"], item["event"])
            if key in self._transitions:
                raise ValueError("Duplicate transition: {0}/{1}".format(*key))
            self._transitions[key] = item

    def dispatch(self, event):
        key = (self.state, event)
        item = self._transitions.get(key)
        if item is None:
            raise InvalidTransition("Invalid transition: {0}/{1}".format(*key))
        previous = self.state
        self.state = item["to"]
        return TransitionResult(previous, event, self.state, item["effects"])
