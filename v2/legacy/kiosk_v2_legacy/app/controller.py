# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class EffectExecutionError(RuntimeError):
    pass


class AppController(object):
    def __init__(self, state_machine, effects, audit=None):
        self.machine = state_machine
        self.effects = effects
        self.audit = audit

    @property
    def state(self):
        return self.machine.state

    def handle(self, event):
        previous = self.machine.state
        transition = self.machine.dispatch(event)
        completed = []
        failed_effect = None
        try:
            for effect in transition.effects:
                failed_effect = effect
                self.effects.run(effect)
                completed.append(effect)
        except Exception as error:
            for effect in reversed(completed):
                self.effects.rollback(effect)
            self.machine.state = previous
            self._audit(
                "effect_failed",
                "Error",
                fromState=previous,
                transitionEvent=event,
                failedEffect=failed_effect,
                errorType=error.__class__.__name__,
                rolledBackEffects=tuple(reversed(completed)),
            )
            raise EffectExecutionError(
                "Effect failed: {0} ({1})".format(
                    failed_effect, error.__class__.__name__
                )
            )
        self._audit(
            "state_transition",
            "Info",
            fromState=previous,
            toState=transition.to_state,
            transitionEvent=event,
            effects=tuple(transition.effects),
        )
        return transition

    def _audit(self, event_name, level, **fields):
        if self.audit is None:
            return
        try:
            self.audit.emit(event_name, level=level, **fields)
        except Exception:
            return
