"""
Basic tests for Network Monitor
"""
import pytest
import tempfile
import os
from app import create_app, db
from app.models import Device, DeviceStatus

@pytest.fixture
def app():
    """Create test app."""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()

def test_app_creation(app):
    """Test app creation."""
    assert app is not None
    assert app.config['TESTING'] is True

def test_database_models(app):
    """Test database models."""
    with app.app_context():
        # Create a test device
        device = Device(
            name='Test Device',
            ip_address='192.168.1.100',
            description='Test device for unit testing',
            status=DeviceStatus.UNKNOWN
        )
        
        db.session.add(device)
        db.session.commit()
        
        # Verify device was created
        saved_device = Device.query.filter_by(name='Test Device').first()
        assert saved_device is not None
        assert saved_device.ip_address == '192.168.1.100'
        assert saved_device.status == DeviceStatus.UNKNOWN

def test_dashboard_route(client):
    """Test dashboard route."""
    response = client.get('/')
    assert response.status_code == 200

def test_api_devices_route(client):
    """Test API devices route."""
    response = client.get('/api/devices')
    assert response.status_code == 200
    assert response.is_json

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
