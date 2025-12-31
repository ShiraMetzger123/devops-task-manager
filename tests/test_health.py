import pytest
import sys
import os

# Add the app directory to the path so we can import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}