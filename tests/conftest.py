import pytest
from fastapi.testclient import TestClient
from app.main import app

# With TestClient we are simulating the browser
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c