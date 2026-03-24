import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.crud import crud_user, crud_org

# With TestClient we are simulating the browser
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.crud import crud_user, crud_org

# With TestClient we are simulating the browser
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Unified Mocking Database for the entire app
@pytest.fixture(autouse=True)
def mock_database(tmp_path, monkeypatch):
    """
    Sets up the temporary JSON databases for Users, Orgs, and Invitations.
    Automatically active for every test.
    """
    # Create temporary directories
    temp_users_dir = tmp_path / "test_users"
    temp_orgs_dir = tmp_path / "test_orgs"
    temp_inv_dir = tmp_path / "test_invitations"
    
    temp_users_dir.mkdir(exist_ok=True)
    temp_orgs_dir.mkdir(exist_ok=True)
    temp_inv_dir.mkdir(exist_ok=True)

    # Forcing code to use new tmp dirs
    monkeypatch.setattr(crud_user, "DATA_DIR_USERS", str(temp_users_dir))
    monkeypatch.setattr(crud_user, "DATA_INV_DIR", str(temp_inv_dir))

    monkeypatch.setattr(crud_org, "DATA_DIR_ORGS", str(temp_orgs_dir))
    monkeypatch.setattr(crud_org, "DATA_INV_DIR", str(temp_inv_dir))

    # Starting tests
    yield

    # After testing, the entire tmp_path tree is automatically deleted by pytest