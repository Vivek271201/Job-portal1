import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_tmp = Path(tempfile.mkdtemp())
# Tests use a throw-away SQLite database and upload folder (never your MySQL data).
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}")
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture(scope="session")
def app_module():
    import app as app_module
    from database.connection import engine
    from database.models import Base
    Base.metadata.drop_all(engine)
    return app_module


@pytest.fixture(scope="session")
def make_client(app_module):
    clients = []
    with TestClient(app_module.app) as first:  # runs startup (creates tables)
        clients.append(first)

        def factory():
            c = TestClient(app_module.app)
            clients.append(c)
            return c
        yield factory


def token(client):
    html = client.get("/about").text
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


class Session:
    """Small helper that adds the CSRF token to every POST."""

    def __init__(self, client):
        self.c = client

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, data=None, files=None, follow_redirects=False, csrf=True):
        data = dict(data or {})
        if csrf:
            data["csrf_token"] = token(self.c)
        return self.c.post(url, data=data, files=files, follow_redirects=follow_redirects)

    def register(self, role, name, email, pw="Secret123"):
        return self.post("/register", {"role": role, "name": name, "email": email,
                                       "password": pw, "confirm_password": pw}, follow_redirects=True)

    def login(self, email, pw="Secret123"):
        return self.post("/login", {"email": email, "password": pw}, follow_redirects=True)


@pytest.fixture(scope="session")
def new_session(make_client):
    return lambda: Session(make_client())
