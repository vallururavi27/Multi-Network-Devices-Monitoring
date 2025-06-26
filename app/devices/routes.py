"""
Device management routes
"""
from flask import render_template, request, jsonify, flash, redirect, url_for, send_file
from datetime import datetime, timedelta
import os
import tempfile

from app.devices import bp
from app import db
from app.models import Device, PingResult, SpeedTestResult, DeviceStatus
from app.monitoring.monitor import NetworkMonitor
from app.utils.excel import ExcelManager

@bp.route('/')
def index():
    """Device list page."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    # Build query
    query = Device.query
    
    if search:
        query = query.filter(
            db.or_(
                Device.name.contains(search),
                Device.ip_address.contains(search),
                Device.description.contains(search)
            )
        )
    
    if status_filter:
        query = query.filter(Device.status == DeviceStatus(status_filter))
    
    # Paginate results
    devices = query.order_by(Device.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('devices/index.html', 
                         devices=devices, 
                         search=search, 
                         status_filter=status_filter)

@bp.route('/add')
def add():
    """Add device page."""
    return render_template('devices/add.html')

@bp.route('/add', methods=['POST'])
def create():
    """Create new device."""
    try:
        device = Device(
            name=request.form['name'],
            ip_address=request.form['ip_address'],
            description=request.form.get('description', ''),
            device_type=request.form.get('device_type', 'server'),
            location=request.form.get('location', ''),
            ping_enabled=bool(request.form.get('ping_enabled')),
            speed_test_enabled=bool(request.form.get('speed_test_enabled')),
            alert_enabled=bool(request.form.get('alert_enabled')),
            ping_interval=int(request.form.get('ping_interval', 60)),
            ping_timeout=int(request.form.get('ping_timeout', 5)),
            alert_threshold_latency=float(request.form.get('alert_threshold_latency', 1000)),
            alert_threshold_packet_loss=float(request.form.get('alert_threshold_packet_loss', 10))
        )
        
        db.session.add(device)
        db.session.commit()
        
        flash(f'Device {device.name} added successfully!', 'success')
        return redirect(url_for('devices.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding device: {str(e)}', 'error')
        return render_template('devices/add.html')

@bp.route('/<int:device_id>')
def detail(device_id):
    """Device detail page."""
    device = Device.query.get_or_404(device_id)
    
    # Get recent ping results
    recent_pings = PingResult.query.filter_by(device_id=device_id)\
        .order_by(PingResult.timestamp.desc())\
        .limit(50).all()
    
    # Get recent speed test results
    recent_speeds = SpeedTestResult.query.filter_by(device_id=device_id)\
        .order_by(SpeedTestResult.timestamp.desc())\
        .limit(10).all()
    
    # Calculate uptime for last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)
    ping_24h = PingResult.query.filter(
        PingResult.device_id == device_id,
        PingResult.timestamp >= last_24h
    ).all()
    
    uptime_stats = {
        'total_pings': len(ping_24h),
        'successful_pings': len([p for p in ping_24h if p.is_reachable]),
        'uptime_percentage': 0
    }
    
    if uptime_stats['total_pings'] > 0:
        uptime_stats['uptime_percentage'] = round(
            (uptime_stats['successful_pings'] / uptime_stats['total_pings']) * 100, 2
        )
    
    return render_template('devices/detail.html', 
                         device=device,
                         recent_pings=recent_pings,
                         recent_speeds=recent_speeds,
                         uptime_stats=uptime_stats)

@bp.route('/<int:device_id>/edit')
def edit(device_id):
    """Edit device page."""
    device = Device.query.get_or_404(device_id)
    return render_template('devices/edit.html', device=device)

@bp.route('/<int:device_id>/edit', methods=['POST'])
def update(device_id):
    """Update device."""
    device = Device.query.get_or_404(device_id)
    
    try:
        device.name = request.form['name']
        device.ip_address = request.form['ip_address']
        device.description = request.form.get('description', '')
        device.device_type = request.form.get('device_type', 'server')
        device.location = request.form.get('location', '')
        device.ping_enabled = bool(request.form.get('ping_enabled'))
        device.speed_test_enabled = bool(request.form.get('speed_test_enabled'))
        device.alert_enabled = bool(request.form.get('alert_enabled'))
        device.ping_interval = int(request.form.get('ping_interval', 60))
        device.ping_timeout = int(request.form.get('ping_timeout', 5))
        device.alert_threshold_latency = float(request.form.get('alert_threshold_latency', 1000))
        device.alert_threshold_packet_loss = float(request.form.get('alert_threshold_packet_loss', 10))
        device.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Device {device.name} updated successfully!', 'success')
        return redirect(url_for('devices.detail', device_id=device_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating device: {str(e)}', 'error')
        return render_template('devices/edit.html', device=device)

@bp.route('/<int:device_id>/delete', methods=['POST'])
def delete(device_id):
    """Delete device."""
    device = Device.query.get_or_404(device_id)
    
    try:
        device_name = device.name
        db.session.delete(device)
        db.session.commit()
        
        flash(f'Device {device_name} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting device: {str(e)}', 'error')
    
    return redirect(url_for('devices.index'))

@bp.route('/<int:device_id>/test', methods=['POST'])
def test_device(device_id):
    """Test device connectivity."""
    device = Device.query.get_or_404(device_id)
    
    try:
        monitor = NetworkMonitor()
        result = monitor.monitor_device(device)
        
        return jsonify({
            'success': True,
            'result': {
                'is_reachable': result.get('ping_result', {}).get('is_reachable', False),
                'response_time': result.get('ping_result', {}).get('response_time'),
                'status': result.get('current_status').value if result.get('current_status') else 'unknown'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/<int:device_id>/toggle', methods=['POST'])
def toggle_device(device_id):
    """Toggle device active status."""
    device = Device.query.get_or_404(device_id)
    
    try:
        device.is_active = not device.is_active
        device.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'enabled' if device.is_active else 'disabled'
        flash(f'Device {device.name} {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling device: {str(e)}', 'error')
    
    return redirect(url_for('devices.index'))

@bp.route('/import')
def import_page():
    """Device import page."""
    return render_template('devices/import.html')

@bp.route('/import', methods=['POST'])
def import_devices():
    """Import devices from Excel file."""
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('devices.import_page'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('devices.import_page'))
        
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('Please upload an Excel file (.xlsx or .xls)', 'error')
            return redirect(url_for('devices.import_page'))
        
        # Save uploaded file temporarily
        temp_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(temp_path)
        
        # Import devices
        excel_manager = ExcelManager()
        result = excel_manager.import_devices_from_excel(temp_path)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if result['success']:
            message = f"Import completed! Imported: {result['devices_imported']}, Updated: {result['devices_updated']}, Skipped: {result['devices_skipped']}"
            flash(message, 'success')
            
            if result['warnings']:
                for warning in result['warnings']:
                    flash(warning, 'warning')
        else:
            flash('Import failed!', 'error')
            for error in result['errors']:
                flash(error, 'error')
        
    except Exception as e:
        flash(f'Import error: {str(e)}', 'error')
    
    return redirect(url_for('devices.index'))

@bp.route('/export')
def export_devices():
    """Export devices to Excel file."""
    try:
        excel_manager = ExcelManager()
        file_path = excel_manager.export_devices_to_excel()
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"devices_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Export error: {str(e)}', 'error')
        return redirect(url_for('devices.index'))

@bp.route('/bulk-action', methods=['POST'])
def bulk_action():
    """Perform bulk actions on devices."""
    try:
        action = request.form.get('action')
        device_ids = request.form.getlist('device_ids')
        
        if not device_ids:
            flash('No devices selected', 'warning')
            return redirect(url_for('devices.index'))
        
        device_ids = [int(id) for id in device_ids]
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        
        if action == 'enable':
            for device in devices:
                device.is_active = True
                device.updated_at = datetime.utcnow()
            flash(f'Enabled {len(devices)} devices', 'success')
            
        elif action == 'disable':
            for device in devices:
                device.is_active = False
                device.updated_at = datetime.utcnow()
            flash(f'Disabled {len(devices)} devices', 'success')
            
        elif action == 'delete':
            for device in devices:
                db.session.delete(device)
            flash(f'Deleted {len(devices)} devices', 'success')
            
        elif action == 'test':
            # Queue monitoring tasks for selected devices
            from app.tasks import monitor_device_by_id
            for device_id in device_ids:
                monitor_device_by_id.delay(device_id)
            flash(f'Queued monitoring tests for {len(devices)} devices', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Bulk action error: {str(e)}', 'error')
    
    return redirect(url_for('devices.index'))
