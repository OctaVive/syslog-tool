import os
import tempfile

import pytest

_test_db = os.path.join(tempfile.gettempdir(), "syslog_tool_pytest.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db.replace(os.sep, '/')}"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    yield
    if os.path.exists(_test_db):
        os.remove(_test_db)
