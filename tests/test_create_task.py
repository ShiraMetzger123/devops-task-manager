import pytest
import sys
import os
import json

# Add the app directory to the path so we can import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

@pytest.fixture
def client():
    # Set environment variable to use SQLite for testing
    os.environ['TESTING'] = 'True'
    
    # Import here to avoid database connection issues
    from app import app, db
    
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_create_task_success(client):
    """Test successful task creation via API"""
    task_data = {
        "title": "Test Task",
        "description": "Test description",
        "priority": "high"
    }
    
    response = client.post('/api/tasks', 
                          data=json.dumps(task_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    assert response.is_json
    
    response_data = response.get_json()
    assert 'id' in response_data
    assert response_data['title'] == "Test Task"

def test_create_task_missing_title(client):
    """Test task creation fails without title"""
    task_data = {
        "description": "Test description without title"
    }
    
    response = client.post('/api/tasks',
                          data=json.dumps(task_data),
                          content_type='application/json')
    
    assert response.status_code == 400