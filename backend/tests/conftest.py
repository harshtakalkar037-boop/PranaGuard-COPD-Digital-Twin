import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
@pytest.fixture(scope='session')
def client(tmp_path_factory):
    db=tmp_path_factory.mktemp('pg-db')/'test.sqlite'
    with TestClient(create_app(db)) as c:yield c
@pytest.fixture()
def engine(client):
    e=client.app.state.engine;e.reset();return e
