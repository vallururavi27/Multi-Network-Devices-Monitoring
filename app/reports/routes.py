"""
Reports routes
"""
from flask import render_template, request, send_file
from datetime import datetime, timedelta

from app.reports import bp
from app.utils.excel import ExcelManager

@bp.route('/')
def index():
    """Reports page."""
    return render_template('reports/index.html')

@bp.route('/export')
def export():
    """Export monitoring data."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.fromisoformat(start_date)
    else:
        start_date = datetime.utcnow() - timedelta(days=7)
    
    if end_date:
        end_date = datetime.fromisoformat(end_date)
    else:
        end_date = datetime.utcnow()
    
    excel_manager = ExcelManager()
    file_path = excel_manager.export_monitoring_results(start_date, end_date)
    
    return send_file(file_path, as_attachment=True)
