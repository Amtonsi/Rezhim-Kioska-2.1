# -*- coding: utf-8 -*-


class EffectExecutionError(RuntimeError):
    pass


class AppController(object):
    def __init__(self, state_machine, effects):
        self.machine = state_machine
        self.effects = effects

    @property
    def state(self):
        return self.machine.state

    def handle(self, event):
        previous = self.machine.state
        transition = self.machine.dispatch(event)
        completed = []
        try:
            for effect in transition.effects:
                self.effects.run(effect)
                completed.append(effect)
        except Exception as error:
            for effect in reversed(completed):
                self.effects.rollback(effect)
            self.machine.state = previous
            raise EffectExecutionError(str(error))
        return transition
