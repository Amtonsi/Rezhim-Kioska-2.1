try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.admin_session import AdminSession


class FakeClock(object):
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class AdminSessionTests(unittest.TestCase):
    def test_session_starts_with_limited_lifetime(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=300, time_func=clock, logger=logger)

        session.start("Admin")

        self.assertTrue(session.is_active())
        self.assertEqual("Admin", session.username)
        self.assertEqual(400.0, session.expires_at)
        self.assertIn(("info", "admin.session_started"), [(level, event) for level, event, _ in logger.events])

    def test_session_times_out_and_logs_return_to_kiosk(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=10, time_func=clock, logger=logger)
        session.start("Admin")

        clock.now = 111.0

        self.assertFalse(session.is_active())
        self.assertIn(("warning", "admin.session_timeout"), [(level, event) for level, event, _ in logger.events])

    def test_session_close_returns_to_kiosk(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=300, time_func=clock, logger=logger)
        session.start("Admin")

        session.close(reason="manual")

        self.assertFalse(session.is_active())
        self.assertIn(("info", "admin.session_closed"), [(level, event) for level, event, _ in logger.events])

    def test_log_data_does_not_include_password_or_token(self):
        session = AdminSession(timeout_seconds=300, time_func=FakeClock())
        session.start("Admin")

        text = str(session.to_log_data())

        self.assertIn("Admin", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("token", text.lower())


if __name__ == "__main__":
    unittest.main()
