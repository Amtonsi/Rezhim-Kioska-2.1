# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class LauncherBootstrap(object):
    def __init__(
        self,
        config_repository,
        settings_factory,
        dpi,
        root_factory,
        session_factory,
        operator_guard,
    ):
        self.config_repository = config_repository
        self.settings_factory = settings_factory
        self.dpi = dpi
        self.root_factory = root_factory
        self.session_factory = session_factory
        self.operator_guard = operator_guard

    def run(self):
        config = self.config_repository.load(require_existing_app=False)
        self.operator_guard.validate(config["operatorUser"])
        settings = self.settings_factory.build(config)
        self.dpi.enable()
        root = self.root_factory()
        session = self.session_factory(root, settings, config)
        try:
            session.start()
            root.mainloop()
        except BaseException:
            self._close_on_error(session)
            raise
        session.close()
        return 0

    def _close_on_error(self, session):
        try:
            session.close()
        except Exception:
            pass
