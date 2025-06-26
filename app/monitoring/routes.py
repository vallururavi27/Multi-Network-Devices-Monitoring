"""
Monitoring routes
"""
from flask import render_template, request, jsonify
from datetime import datetime, timedelta

from app.monitoring import bp
from app import db
from app.models import Device, PingResult, SpeedTestResult, Alert

@bp.route('/')
def index():
    """Monitoring overview page."""
    # Get recent monitoring activity
    recent_pings = PingResult.query.join(Device)\
        .order_by(PingResult.timestamp.desc())\
        .limit(50).all()
    
    recent_speeds = SpeedTestResult.query.join(Device)\
        .order_by(SpeedTestResult.timestamp.desc())\
        .limit(20).all()
    
    return render_template('monitoring/index.html',
                         recent_pings=recent_pings,
                         recent_speeds=recent_speeds)

@bp.route('/alerts')
def alerts():
    """Alerts page."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    alerts = Alert.query.join(Device)\
        .order_by(Alert.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('monitoring/alerts.html', alerts=alerts)

@bp.route('/live')
def live():
    """Live monitoring page."""
    return render_template('monitoring/live.html')
