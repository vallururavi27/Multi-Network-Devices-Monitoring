"""
API routes for network monitoring
"""
from flask import request, jsonify
from datetime import datetime, timedelta

from app.api import bp
from app import db
from app.models import Device, PingResult, SpeedTestResult, Alert
from app.monitoring.monitor import NetworkMonitor
from app.tasks import monitor_device_by_id, run_speed_test

@bp.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices."""
    devices = Device.query.filter_by(is_active=True).all()
    return jsonify([device.to_dict() for device in devices])

@bp.route('/devices', methods=['POST'])
def create_device():
    """Create a new device."""
    try:
        data = request.get_json()
        
        device = Device(
            name=data['name'],
            ip_address=data['ip_address'],
            description=data.get('description', ''),
            device_type=data.get('device_type', 'server'),
            location=data.get('location', ''),
            ping_enabled=data.get('ping_enabled', True),
            speed_test_enabled=data.get('speed_test_enabled', False),
            alert_enabled=data.get('alert_enabled', True)
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify(device.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Get device by ID."""
    device = Device.query.get_or_404(device_id)
    return jsonify(device.to_dict())

@bp.route('/devices/<int:device_id>/status', methods=['GET'])
def get_device_status(device_id):
    """Get device status and recent results."""
    device = Device.query.get_or_404(device_id)
    
    # Get recent ping results
    recent_pings = PingResult.query.filter_by(device_id=device_id)\
        .order_by(PingResult.timestamp.desc())\
        .limit(10).all()
    
    # Get recent speed test results
    recent_speeds = SpeedTestResult.query.filter_by(device_id=device_id)\
        .order_by(SpeedTestResult.timestamp.desc())\
        .limit(5).all()
    
    return jsonify({
        'device': device.to_dict(),
        'recent_pings': [ping.to_dict() for ping in recent_pings],
        'recent_speeds': [speed.to_dict() for speed in recent_speeds]
    })

@bp.route('/devices/<int:device_id>/test', methods=['POST'])
def test_device(device_id):
    """Queue monitoring test for device."""
    device = Device.query.get_or_404(device_id)
    
    # Queue monitoring task
    task = monitor_device_by_id.delay(device_id)
    
    return jsonify({
        'message': f'Monitoring test queued for {device.name}',
        'task_id': task.id
    })

@bp.route('/devices/<int:device_id>/speed-test', methods=['POST'])
def speed_test_device(device_id):
    """Queue speed test for device."""
    device = Device.query.get_or_404(device_id)
    
    if not device.speed_test_enabled:
        return jsonify({'error': 'Speed test not enabled for this device'}), 400
    
    # Queue speed test task
    task = run_speed_test.delay(device_id)
    
    return jsonify({
        'message': f'Speed test queued for {device.name}',
        'task_id': task.id
    })

@bp.route('/monitoring/results', methods=['GET'])
def get_monitoring_results():
    """Get monitoring results with filtering."""
    # Parse query parameters
    device_id = request.args.get('device_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    result_type = request.args.get('type', 'ping')  # ping or speed
    limit = request.args.get('limit', 100, type=int)
    
    # Parse dates
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start_date = datetime.utcnow() - timedelta(hours=24)
    
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end_date = datetime.utcnow()
    
    if result_type == 'ping':
        query = PingResult.query
        if device_id:
            query = query.filter_by(device_id=device_id)
        
        results = query.filter(
            PingResult.timestamp >= start_date,
            PingResult.timestamp <= end_date
        ).order_by(PingResult.timestamp.desc()).limit(limit).all()
        
        return jsonify([result.to_dict() for result in results])
    
    elif result_type == 'speed':
        query = SpeedTestResult.query
        if device_id:
            query = query.filter_by(device_id=device_id)
        
        results = query.filter(
            SpeedTestResult.timestamp >= start_date,
            SpeedTestResult.timestamp <= end_date
        ).order_by(SpeedTestResult.timestamp.desc()).limit(limit).all()
        
        return jsonify([result.to_dict() for result in results])
    
    else:
        return jsonify({'error': 'Invalid result type'}), 400

@bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get alerts with filtering."""
    device_id = request.args.get('device_id', type=int)
    is_active = request.args.get('is_active', type=bool)
    limit = request.args.get('limit', 50, type=int)
    
    query = Alert.query
    
    if device_id:
        query = query.filter_by(device_id=device_id)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    return jsonify([alert.to_dict() for alert in alerts])

@bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    alert = Alert.query.get_or_404(alert_id)
    
    try:
        data = request.get_json() or {}
        
        alert.is_acknowledged = True
        alert.acknowledged_by = data.get('acknowledged_by', 'API User')
        alert.acknowledged_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(alert.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/status', methods=['GET'])
def system_status():
    """Get system status summary."""
    monitor = NetworkMonitor()
    status_summary = monitor.get_device_status_summary()
    
    # Get active alerts count
    active_alerts = Alert.query.filter_by(is_active=True).count()
    
    return jsonify({
        'device_summary': status_summary,
        'active_alerts': active_alerts,
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers for API
@bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@bp.errorhandler(400)
def api_bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
