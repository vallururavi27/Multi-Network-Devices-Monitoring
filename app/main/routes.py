"""
Main application routes
"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from sqlalchemy import func

from app.main import bp
from app import db
from app.models import Device, PingResult, SpeedTestResult, Alert, DeviceStatus, SystemSettings
from app.monitoring.monitor import NetworkMonitor

@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    """Main dashboard view."""
    # Get device status summary
    monitor = NetworkMonitor()
    status_summary = monitor.get_device_status_summary()
    
    # Get recent alerts
    recent_alerts = Alert.query.filter_by(is_active=True)\
        .order_by(Alert.created_at.desc())\
        .limit(10).all()
    
    # Get recent ping results for chart
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_pings = db.session.query(
        PingResult.timestamp,
        func.count(PingResult.id).label('total'),
        func.sum(func.cast(PingResult.is_reachable, db.Integer)).label('successful')
    ).filter(
        PingResult.timestamp >= last_24h
    ).group_by(
        func.strftime('%Y-%m-%d %H', PingResult.timestamp)
    ).order_by(PingResult.timestamp).all()
    
    # Prepare chart data
    chart_data = {
        'labels': [],
        'successful': [],
        'failed': []
    }
    
    for ping in recent_pings:
        chart_data['labels'].append(ping.timestamp.strftime('%H:00'))
        chart_data['successful'].append(int(ping.successful or 0))
        chart_data['failed'].append(int(ping.total) - int(ping.successful or 0))
    
    return render_template('dashboard.html',
                         status_summary=status_summary,
                         recent_alerts=recent_alerts,
                         chart_data=chart_data)

@bp.route('/status')
def status():
    """System status page."""
    # Get system information
    total_devices = Device.query.filter_by(is_active=True).count()
    
    # Get ping statistics for last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)
    ping_stats = db.session.query(
        func.count(PingResult.id).label('total_pings'),
        func.sum(func.cast(PingResult.is_reachable, db.Integer)).label('successful_pings')
    ).filter(PingResult.timestamp >= last_24h).first()
    
    # Get speed test statistics
    speed_stats = db.session.query(
        func.count(SpeedTestResult.id).label('total_tests'),
        func.avg(SpeedTestResult.download_speed).label('avg_download'),
        func.avg(SpeedTestResult.upload_speed).label('avg_upload')
    ).filter(SpeedTestResult.timestamp >= last_24h).first()
    
    # Get alert statistics
    alert_stats = db.session.query(
        func.count(Alert.id).label('total_alerts'),
        func.sum(func.cast(Alert.is_active, db.Integer)).label('active_alerts')
    ).filter(Alert.created_at >= last_24h).first()
    
    system_info = {
        'total_devices': total_devices,
        'total_pings': ping_stats.total_pings or 0,
        'successful_pings': ping_stats.successful_pings or 0,
        'ping_success_rate': round((ping_stats.successful_pings or 0) / max(ping_stats.total_pings or 1, 1) * 100, 2),
        'total_speed_tests': speed_stats.total_tests or 0,
        'avg_download_speed': round(speed_stats.avg_download or 0, 2),
        'avg_upload_speed': round(speed_stats.avg_upload or 0, 2),
        'total_alerts': alert_stats.total_alerts or 0,
        'active_alerts': alert_stats.active_alerts or 0
    }
    
    return render_template('status.html', system_info=system_info)

@bp.route('/api/dashboard/data')
def dashboard_data():
    """API endpoint for dashboard data (for AJAX updates)."""
    monitor = NetworkMonitor()
    status_summary = monitor.get_device_status_summary()
    
    # Get recent alerts count
    active_alerts = Alert.query.filter_by(is_active=True).count()
    
    # Get latest ping results
    latest_pings = db.session.query(
        Device.name,
        Device.ip_address,
        Device.status,
        PingResult.response_time,
        PingResult.timestamp
    ).join(PingResult).filter(
        Device.is_active == True
    ).order_by(PingResult.timestamp.desc()).limit(10).all()
    
    ping_data = []
    for ping in latest_pings:
        ping_data.append({
            'device_name': ping.name,
            'ip_address': ping.ip_address,
            'status': ping.status.value if ping.status else 'unknown',
            'response_time': ping.response_time,
            'timestamp': ping.timestamp.isoformat()
        })
    
    return jsonify({
        'status_summary': status_summary,
        'active_alerts': active_alerts,
        'latest_pings': ping_data,
        'timestamp': datetime.utcnow().isoformat()
    })

@bp.route('/settings')
def settings():
    """System settings page."""
    settings = SystemSettings.query.all()
    settings_dict = {s.key: s for s in settings}
    
    return render_template('settings.html', settings=settings_dict)

@bp.route('/settings', methods=['POST'])
def update_settings():
    """Update system settings."""
    try:
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                setting = SystemSettings.query.filter_by(key=setting_key).first()
                
                if setting:
                    setting.value = value
                    setting.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('main.settings'))

@bp.route('/test-email', methods=['POST'])
def test_email():
    """Test email configuration."""
    try:
        from app.alerts.email import EmailAlertManager
        
        email_manager = EmailAlertManager()
        recipient = request.form.get('email', '')
        
        if not recipient:
            return jsonify({'success': False, 'message': 'Email address is required'})
        
        success = email_manager.send_test_email(recipient)
        
        if success:
            return jsonify({'success': True, 'message': 'Test email sent successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send test email'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@bp.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check if we have devices
        device_count = Device.query.count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'devices': device_count
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')

# Error handlers
@bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
