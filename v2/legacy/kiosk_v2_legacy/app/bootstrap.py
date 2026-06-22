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
    ):
        self.config_repository = config_repository
        self.settings_factory = settings_factory
        self.dpi = dpi
        self.root_factory = root_factory
        self.session_factory = session_factory

    def run(self):
        config = self.config_repository.load(require_existing_app=False)
        settings = self.settings_factory.build(config)
        self.dpi.enable()
        root = self.root_factory()
        session = self.session_factory(root, settings, config)
        session.start()
        try:
            root.mainloop()
        finally:
            session.close()
        return 0
