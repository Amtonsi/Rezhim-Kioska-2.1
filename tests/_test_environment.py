import os
import tempfile


TEST_LOG_DIRECTORY = os.path.join(tempfile.gettempdir(), "python-kiosk-tests")
TEST_LOG_PATH = os.path.join(TEST_LOG_DIRECTORY, "kiosk.log")

os.environ.setdefault("PYTHONKIOSK_LOG_PATH", TEST_LOG_PATH)
os.environ.setdefault("PYTHONKIOSK_SESSION_ID", "unit-tests")
