"""
Excel import/export utilities for network monitoring
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
import ipaddress
import tempfile

from app import db
from app.models import Device, PingResult, SpeedTestResult, Alert, DeviceStatus

logger = logging.getLogger(__name__)

class ExcelManager:
    """Handles Excel import/export operations."""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def import_devices_from_excel(self, file_path: str) -> Dict:
        """
        Import devices from Excel file.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Dictionary with import results
        """
        result = {
            'success': False,
            'devices_imported': 0,
            'devices_updated': 0,
            'devices_skipped': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = ['name', 'ip_address']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                result['errors'].append(f"Missing required columns: {', '.join(missing_columns)}")
                return result
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    device_result = self._process_device_row(row, index + 2)  # +2 for header and 0-based index
                    
                    if device_result['action'] == 'imported':
                        result['devices_imported'] += 1
                    elif device_result['action'] == 'updated':
                        result['devices_updated'] += 1
                    elif device_result['action'] == 'skipped':
                        result['devices_skipped'] += 1
                    
                    if device_result.get('warning'):
                        result['warnings'].append(f"Row {index + 2}: {device_result['warning']}")
                        
                except Exception as e:
                    error_msg = f"Row {index + 2}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(f"Error processing row {index + 2}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            result['success'] = True
            
        except Exception as e:
            db.session.rollback()
            result['errors'].append(f"File processing error: {str(e)}")
            logger.error(f"Excel import error: {str(e)}")
        
        return result
    
    def _process_device_row(self, row: pd.Series, row_number: int) -> Dict:
        """
        Process a single device row from Excel.
        
        Args:
            row: Pandas Series representing the row
            row_number: Row number for error reporting
            
        Returns:
            Dictionary with processing result
        """
        result = {'action': 'skipped', 'warning': None}
        
        # Extract and validate data
        name = str(row.get('name', '')).strip()
        ip_address = str(row.get('ip_address', '')).strip()
        
        if not name or not ip_address:
            raise ValueError("Name and IP address are required")
        
        # Validate IP address
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")
        
        # Check if device already exists
        existing_device = Device.query.filter_by(ip_address=ip_address).first()
        
        if existing_device:
            # Update existing device
            existing_device.name = name
            existing_device.description = str(row.get('description', '')).strip() or existing_device.description
            existing_device.device_type = str(row.get('device_type', '')).strip() or existing_device.device_type
            existing_device.location = str(row.get('location', '')).strip() or existing_device.location
            existing_device.updated_at = datetime.utcnow()
            
            result['action'] = 'updated'
            result['warning'] = f"Updated existing device with IP {ip_address}"
        else:
            # Create new device
            device = Device(
                name=name,
                ip_address=ip_address,
                description=str(row.get('description', '')).strip(),
                device_type=str(row.get('device_type', 'server')).strip(),
                location=str(row.get('location', '')).strip(),
                ping_enabled=self._parse_boolean(row.get('ping_enabled', True)),
                speed_test_enabled=self._parse_boolean(row.get('speed_test_enabled', False)),
                alert_enabled=self._parse_boolean(row.get('alert_enabled', True)),
                ping_interval=int(row.get('ping_interval', 60)),
                ping_timeout=int(row.get('ping_timeout', 5)),
                status=DeviceStatus.UNKNOWN
            )
            
            db.session.add(device)
            result['action'] = 'imported'
        
        return result
    
    def _parse_boolean(self, value) -> bool:
        """Parse boolean value from Excel cell."""
        if pd.isna(value):
            return True
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on', 'enabled')
        
        return bool(value)
    
    def export_devices_to_excel(self, file_path: Optional[str] = None) -> str:
        """
        Export all devices to Excel file.
        
        Args:
            file_path: Optional file path (generates temp file if not provided)
            
        Returns:
            Path to generated Excel file
        """
        if not file_path:
            file_path = os.path.join(self.temp_dir, f"devices_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        # Get all devices
        devices = Device.query.all()
        
        # Create DataFrame
        data = []
        for device in devices:
            data.append({
                'id': device.id,
                'name': device.name,
                'ip_address': device.ip_address,
                'description': device.description,
                'device_type': device.device_type,
                'location': device.location,
                'status': device.status.value if device.status else 'unknown',
                'ping_enabled': device.ping_enabled,
                'speed_test_enabled': device.speed_test_enabled,
                'alert_enabled': device.alert_enabled,
                'ping_interval': device.ping_interval,
                'ping_timeout': device.ping_timeout,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'created_at': device.created_at.isoformat(),
                'is_active': device.is_active
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel file with formatting
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Devices', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Devices']
            
            # Apply formatting
            self._format_devices_worksheet(worksheet, len(data))
        
        logger.info(f"Exported {len(devices)} devices to {file_path}")
        return file_path
    
    def export_monitoring_results(self, start_date: datetime, end_date: datetime, 
                                device_ids: Optional[List[int]] = None, 
                                file_path: Optional[str] = None) -> str:
        """
        Export monitoring results to Excel file.
        
        Args:
            start_date: Start date for data export
            end_date: End date for data export
            device_ids: Optional list of device IDs to filter
            file_path: Optional file path
            
        Returns:
            Path to generated Excel file
        """
        if not file_path:
            date_str = start_date.strftime('%Y%m%d')
            file_path = os.path.join(self.temp_dir, f"monitoring_results_{date_str}.xlsx")
        
        # Build device query
        device_query = Device.query
        if device_ids:
            device_query = device_query.filter(Device.id.in_(device_ids))
        devices = device_query.all()
        
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Export ping results
            self._export_ping_results(writer, devices, start_date, end_date)
            
            # Export speed test results
            self._export_speed_results(writer, devices, start_date, end_date)
            
            # Export alerts
            self._export_alerts(writer, devices, start_date, end_date)
            
            # Export summary
            self._export_summary(writer, devices, start_date, end_date)
        
        logger.info(f"Exported monitoring results to {file_path}")
        return file_path
    
    def _export_ping_results(self, writer, devices: List[Device], start_date: datetime, end_date: datetime):
        """Export ping results to Excel sheet."""
        data = []
        
        for device in devices:
            ping_results = PingResult.query.filter(
                PingResult.device_id == device.id,
                PingResult.timestamp >= start_date,
                PingResult.timestamp <= end_date
            ).all()
            
            for result in ping_results:
                data.append({
                    'device_name': device.name,
                    'ip_address': device.ip_address,
                    'timestamp': result.timestamp.isoformat(),
                    'is_reachable': result.is_reachable,
                    'response_time_ms': result.response_time,
                    'packet_loss_percent': result.packet_loss,
                    'error_message': result.error_message
                })
        
        if data:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Ping Results', index=False)
    
    def _export_speed_results(self, writer, devices: List[Device], start_date: datetime, end_date: datetime):
        """Export speed test results to Excel sheet."""
        data = []
        
        for device in devices:
            speed_results = SpeedTestResult.query.filter(
                SpeedTestResult.device_id == device.id,
                SpeedTestResult.timestamp >= start_date,
                SpeedTestResult.timestamp <= end_date
            ).all()
            
            for result in speed_results:
                data.append({
                    'device_name': device.name,
                    'ip_address': device.ip_address,
                    'timestamp': result.timestamp.isoformat(),
                    'download_speed_mbps': result.download_speed,
                    'upload_speed_mbps': result.upload_speed,
                    'ping_latency_ms': result.ping_latency,
                    'server_name': result.server_name,
                    'server_location': result.server_location,
                    'test_duration_sec': result.test_duration,
                    'is_successful': result.is_successful,
                    'error_message': result.error_message
                })
        
        if data:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Speed Test Results', index=False)
    
    def _export_alerts(self, writer, devices: List[Device], start_date: datetime, end_date: datetime):
        """Export alerts to Excel sheet."""
        device_ids = [d.id for d in devices]
        
        alerts = Alert.query.filter(
            Alert.device_id.in_(device_ids),
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        ).all()
        
        data = []
        for alert in alerts:
            data.append({
                'device_name': alert.device.name,
                'ip_address': alert.device.ip_address,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'is_active': alert.is_active,
                'is_acknowledged': alert.is_acknowledged,
                'acknowledged_by': alert.acknowledged_by,
                'created_at': alert.created_at.isoformat(),
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            })
        
        if data:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Alerts', index=False)
    
    def _export_summary(self, writer, devices: List[Device], start_date: datetime, end_date: datetime):
        """Export summary statistics to Excel sheet."""
        data = []
        
        for device in devices:
            # Get ping statistics
            ping_results = PingResult.query.filter(
                PingResult.device_id == device.id,
                PingResult.timestamp >= start_date,
                PingResult.timestamp <= end_date
            ).all()
            
            total_pings = len(ping_results)
            successful_pings = len([p for p in ping_results if p.is_reachable])
            uptime_percentage = (successful_pings / total_pings * 100) if total_pings > 0 else 0
            
            avg_response_time = None
            if successful_pings > 0:
                response_times = [p.response_time for p in ping_results if p.response_time]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            # Get speed test count
            speed_tests = SpeedTestResult.query.filter(
                SpeedTestResult.device_id == device.id,
                SpeedTestResult.timestamp >= start_date,
                SpeedTestResult.timestamp <= end_date
            ).count()
            
            # Get alert count
            alerts = Alert.query.filter(
                Alert.device_id == device.id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            ).count()
            
            data.append({
                'device_name': device.name,
                'ip_address': device.ip_address,
                'device_type': device.device_type,
                'location': device.location,
                'total_pings': total_pings,
                'successful_pings': successful_pings,
                'uptime_percentage': round(uptime_percentage, 2),
                'avg_response_time_ms': round(avg_response_time, 2) if avg_response_time else None,
                'speed_tests_count': speed_tests,
                'alerts_count': alerts,
                'current_status': device.status.value if device.status else 'unknown'
            })
        
        if data:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Summary', index=False)
    
    def _format_devices_worksheet(self, worksheet, row_count: int):
        """Apply formatting to devices worksheet."""
        # Header formatting
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
