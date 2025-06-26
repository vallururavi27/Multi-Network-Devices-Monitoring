"""
Celery background tasks for network monitoring
"""
import logging
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab

from app import create_app, db, make_celery
from app.models import Device, PingResult, SpeedTestResult, Alert, SystemSettings
from app.monitoring.monitor import NetworkMonitor
from app.alerts.email import EmailAlertManager

# Create Flask app and Celery instance
app = create_app()
celery = make_celery(app)

logger = logging.getLogger(__name__)

@celery.task(bind=True)
def monitor_all_devices(self):
    """
    Monitor all active devices - scheduled task.
    """
    with app.app_context():
        try:
            logger.info("Starting scheduled monitoring of all devices")
            
            monitor = NetworkMonitor()
            results = monitor.monitor_devices()
            
            logger.info(f"Completed monitoring of {len(results)} devices")
            
            # Return summary
            summary = {
                'total_devices': len(results),
                'successful': len([r for r in results if 'error' not in r]),
                'failed': len([r for r in results if 'error' in r]),
                'status_changes': len([r for r in results if r.get('status_changed')]),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in monitor_all_devices task: {str(e)}")
            self.retry(countdown=60, max_retries=3)

@celery.task(bind=True)
def monitor_device_by_id(self, device_id):
    """
    Monitor a specific device by ID.
    
    Args:
        device_id: ID of device to monitor
    """
    with app.app_context():
        try:
            device = Device.query.get(device_id)
            if not device:
                logger.error(f"Device with ID {device_id} not found")
                return {'error': f'Device {device_id} not found'}
            
            if not device.is_active:
                logger.info(f"Device {device.name} is not active, skipping")
                return {'skipped': True, 'reason': 'Device not active'}
            
            monitor = NetworkMonitor()
            result = monitor.monitor_device(device)
            
            logger.info(f"Completed monitoring of device {device.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error monitoring device {device_id}: {str(e)}")
            self.retry(countdown=30, max_retries=3)

@celery.task(bind=True)
def run_speed_test(self, device_id):
    """
    Run speed test for a specific device.
    
    Args:
        device_id: ID of device to test
    """
    with app.app_context():
        try:
            device = Device.query.get(device_id)
            if not device:
                return {'error': f'Device {device_id} not found'}
            
            if not device.speed_test_enabled:
                return {'skipped': True, 'reason': 'Speed test not enabled'}
            
            monitor = NetworkMonitor()
            result = monitor._speed_test_device(device)
            
            logger.info(f"Completed speed test for device {device.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error running speed test for device {device_id}: {str(e)}")
            self.retry(countdown=60, max_retries=2)

@celery.task(bind=True)
def send_alert_emails(self):
    """
    Send pending alert emails.
    """
    with app.app_context():
        try:
            # Get unsent alerts
            alerts = Alert.query.filter(
                Alert.is_active == True,
                Alert.email_sent == False,
                Alert.retry_count < 3
            ).all()
            
            if not alerts:
                return {'message': 'No pending alerts to send'}
            
            email_manager = EmailAlertManager()
            sent_count = 0
            failed_count = 0
            
            for alert in alerts:
                try:
                    success = email_manager.send_alert_email(alert)
                    if success:
                        alert.email_sent = True
                        alert.email_sent_at = datetime.utcnow()
                        sent_count += 1
                    else:
                        alert.retry_count += 1
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error sending alert email for alert {alert.id}: {str(e)}")
                    alert.retry_count += 1
                    failed_count += 1
            
            db.session.commit()
            
            logger.info(f"Sent {sent_count} alert emails, {failed_count} failed")
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total_processed': len(alerts)
            }
            
        except Exception as e:
            logger.error(f"Error in send_alert_emails task: {str(e)}")
            self.retry(countdown=300, max_retries=3)  # 5 minute retry

@celery.task
def cleanup_old_data():
    """
    Clean up old monitoring data to prevent database bloat.
    """
    with app.app_context():
        try:
            # Get retention settings
            ping_retention_days = SystemSettings.query.filter_by(
                key='max_ping_history_days'
            ).first()
            retention_days = int(ping_retention_days.value) if ping_retention_days else 30
            
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Delete old ping results
            old_pings = PingResult.query.filter(
                PingResult.timestamp < cutoff_date
            ).delete()
            
            # Delete old speed test results (keep for longer - 90 days)
            speed_cutoff = datetime.utcnow() - timedelta(days=90)
            old_speeds = SpeedTestResult.query.filter(
                SpeedTestResult.timestamp < speed_cutoff
            ).delete()
            
            # Delete resolved alerts older than 30 days
            alert_cutoff = datetime.utcnow() - timedelta(days=30)
            old_alerts = Alert.query.filter(
                Alert.resolved_at < alert_cutoff,
                Alert.is_active == False
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up {old_pings} ping results, {old_speeds} speed tests, {old_alerts} alerts")
            
            return {
                'ping_results_deleted': old_pings,
                'speed_results_deleted': old_speeds,
                'alerts_deleted': old_alerts,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup_old_data task: {str(e)}")
            return {'error': str(e)}

@celery.task
def generate_daily_report():
    """
    Generate daily monitoring report.
    """
    with app.app_context():
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)
            start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get devices
            devices = Device.query.filter_by(is_active=True).all()
            
            report_data = {
                'date': yesterday.date().isoformat(),
                'total_devices': len(devices),
                'device_stats': [],
                'alerts_generated': 0,
                'total_pings': 0,
                'total_speed_tests': 0
            }
            
            for device in devices:
                # Get ping results for the day
                ping_results = PingResult.query.filter(
                    PingResult.device_id == device.id,
                    PingResult.timestamp >= start_of_day,
                    PingResult.timestamp <= end_of_day
                ).all()
                
                # Get speed test results for the day
                speed_results = SpeedTestResult.query.filter(
                    SpeedTestResult.device_id == device.id,
                    SpeedTestResult.timestamp >= start_of_day,
                    SpeedTestResult.timestamp <= end_of_day
                ).all()
                
                # Calculate statistics
                total_pings = len(ping_results)
                successful_pings = len([p for p in ping_results if p.is_reachable])
                uptime_percentage = (successful_pings / total_pings * 100) if total_pings > 0 else 0
                
                avg_response_time = None
                if successful_pings > 0:
                    response_times = [p.response_time for p in ping_results if p.response_time]
                    if response_times:
                        avg_response_time = sum(response_times) / len(response_times)
                
                device_stats = {
                    'device_name': device.name,
                    'ip_address': device.ip_address,
                    'total_pings': total_pings,
                    'successful_pings': successful_pings,
                    'uptime_percentage': round(uptime_percentage, 2),
                    'avg_response_time': round(avg_response_time, 2) if avg_response_time else None,
                    'speed_tests': len(speed_results)
                }
                
                report_data['device_stats'].append(device_stats)
                report_data['total_pings'] += total_pings
                report_data['total_speed_tests'] += len(speed_results)
            
            # Get alerts for the day
            alerts = Alert.query.filter(
                Alert.created_at >= start_of_day,
                Alert.created_at <= end_of_day
            ).count()
            
            report_data['alerts_generated'] = alerts
            
            logger.info(f"Generated daily report for {yesterday.date()}")
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            return {'error': str(e)}

# Celery Beat Schedule
celery.conf.beat_schedule = {
    # Monitor all devices every 5 minutes
    'monitor-all-devices': {
        'task': 'app.tasks.monitor_all_devices',
        'schedule': 300.0,  # 5 minutes
    },
    
    # Send alert emails every 2 minutes
    'send-alert-emails': {
        'task': 'app.tasks.send_alert_emails',
        'schedule': 120.0,  # 2 minutes
    },
    
    # Clean up old data daily at 2 AM
    'cleanup-old-data': {
        'task': 'app.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Generate daily report at 1 AM
    'generate-daily-report': {
        'task': 'app.tasks.generate_daily_report',
        'schedule': crontab(hour=1, minute=0),
    },
}

celery.conf.timezone = 'UTC'
