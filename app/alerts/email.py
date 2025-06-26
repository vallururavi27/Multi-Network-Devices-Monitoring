"""
Email alert system for network monitoring
"""
import logging
from datetime import datetime
from typing import List, Optional
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail
from app.models import Alert, Device, SystemSettings

logger = logging.getLogger(__name__)

class EmailAlertManager:
    """Manages email alerts for network monitoring events."""
    
    def __init__(self):
        self.enabled = self._is_email_enabled()
    
    def _is_email_enabled(self) -> bool:
        """Check if email notifications are enabled."""
        try:
            setting = SystemSettings.query.filter_by(
                key='email_notifications_enabled'
            ).first()
            return setting.get_value() if setting else True
        except Exception:
            return True
    
    def send_alert_email(self, alert: Alert) -> bool:
        """
        Send email notification for an alert.
        
        Args:
            alert: Alert object to send
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Email notifications are disabled")
            return False
        
        try:
            # Get recipients
            recipients = self._get_alert_recipients()
            if not recipients:
                logger.warning("No email recipients configured")
                return False
            
            # Create email message
            subject = self._generate_subject(alert)
            body = self._generate_body(alert)
            html_body = self._generate_html_body(alert)
            
            msg = Message(
                subject=subject,
                recipients=recipients,
                body=body,
                html=html_body
            )
            
            # Send email
            mail.send(msg)
            logger.info(f"Alert email sent for {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
            return False
    
    def send_test_email(self, recipient: str) -> bool:
        """
        Send a test email to verify configuration.
        
        Args:
            recipient: Email address to send test to
            
        Returns:
            True if test email was sent successfully
        """
        try:
            subject = "Network Monitor - Test Email"
            body = """
This is a test email from Network Monitor.

If you received this email, your email configuration is working correctly.

Timestamp: {}
            """.format(datetime.utcnow().isoformat())
            
            msg = Message(
                subject=subject,
                recipients=[recipient],
                body=body
            )
            
            mail.send(msg)
            logger.info(f"Test email sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test email: {str(e)}")
            return False
    
    def send_daily_report(self, report_data: dict, recipients: Optional[List[str]] = None) -> bool:
        """
        Send daily monitoring report via email.
        
        Args:
            report_data: Dictionary containing report data
            recipients: List of email addresses (optional)
            
        Returns:
            True if report was sent successfully
        """
        try:
            if not recipients:
                recipients = self._get_alert_recipients()
            
            if not recipients:
                logger.warning("No recipients for daily report")
                return False
            
            subject = f"Network Monitor Daily Report - {report_data.get('date', 'Unknown')}"
            body = self._generate_report_body(report_data)
            html_body = self._generate_report_html_body(report_data)
            
            msg = Message(
                subject=subject,
                recipients=recipients,
                body=body,
                html=html_body
            )
            
            mail.send(msg)
            logger.info("Daily report email sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {str(e)}")
            return False
    
    def _get_alert_recipients(self) -> List[str]:
        """Get list of email recipients for alerts."""
        try:
            # Get from app config first
            recipients = current_app.config.get('ALERT_EMAIL_RECIPIENTS', [])
            if recipients and isinstance(recipients, list):
                return [r.strip() for r in recipients if r.strip()]
            
            # Get from database settings
            setting = SystemSettings.query.filter_by(
                key='alert_email_recipients'
            ).first()
            
            if setting and setting.value:
                return [r.strip() for r in setting.value.split(',') if r.strip()]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting alert recipients: {str(e)}")
            return []
    
    def _generate_subject(self, alert: Alert) -> str:
        """Generate email subject for alert."""
        severity_prefix = {
            'low': '[INFO]',
            'medium': '[WARNING]',
            'high': '[ALERT]',
            'critical': '[CRITICAL]'
        }.get(alert.severity, '[ALERT]')
        
        return f"{severity_prefix} {alert.title}"
    
    def _generate_body(self, alert: Alert) -> str:
        """Generate plain text email body for alert."""
        device = alert.device
        
        template = """
Network Monitor Alert

Alert: {title}
Severity: {severity}
Device: {device_name} ({ip_address})
Location: {location}
Time: {timestamp}

Details:
{message}

Device Information:
- Type: {device_type}
- Description: {description}
- Last Seen: {last_seen}

---
This is an automated message from Network Monitor.
        """.strip()
        
        return template.format(
            title=alert.title,
            severity=alert.severity.upper(),
            device_name=device.name,
            ip_address=device.ip_address,
            location=device.location or 'Unknown',
            timestamp=alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            message=alert.message,
            device_type=device.device_type or 'Unknown',
            description=device.description or 'No description',
            last_seen=device.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC') if device.last_seen else 'Never'
        )
    
    def _generate_html_body(self, alert: Alert) -> str:
        """Generate HTML email body for alert."""
        device = alert.device
        
        # Color coding for severity
        severity_colors = {
            'low': '#28a745',      # Green
            'medium': '#ffc107',   # Yellow
            'high': '#fd7e14',     # Orange
            'critical': '#dc3545'  # Red
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Network Monitor Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }
        .footer { background-color: #e9ecef; padding: 10px; border-radius: 0 0 5px 5px; font-size: 12px; color: #6c757d; }
        .info-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .info-table th, .info-table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .info-table th { background-color: #e9ecef; font-weight: bold; }
        .severity { font-weight: bold; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Network Monitor Alert</h2>
        </div>
        
        <div class="content">
            <h3>{title}</h3>
            <p><strong>Severity:</strong> <span class="severity" style="color: {color};">{severity}</span></p>
            <p><strong>Time:</strong> {timestamp}</p>
            
            <h4>Device Information</h4>
            <table class="info-table">
                <tr><th>Name</th><td>{device_name}</td></tr>
                <tr><th>IP Address</th><td>{ip_address}</td></tr>
                <tr><th>Type</th><td>{device_type}</td></tr>
                <tr><th>Location</th><td>{location}</td></tr>
                <tr><th>Last Seen</th><td>{last_seen}</td></tr>
            </table>
            
            <h4>Alert Details</h4>
            <p>{message}</p>
            
            {description_section}
        </div>
        
        <div class="footer">
            This is an automated message from Network Monitor.
        </div>
    </div>
</body>
</html>
        """.strip()
        
        description_section = ""
        if device.description:
            description_section = f"<h4>Device Description</h4><p>{device.description}</p>"
        
        return template.format(
            title=alert.title,
            severity=alert.severity,
            color=color,
            device_name=device.name,
            ip_address=device.ip_address,
            device_type=device.device_type or 'Unknown',
            location=device.location or 'Unknown',
            timestamp=alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            message=alert.message,
            last_seen=device.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC') if device.last_seen else 'Never',
            description_section=description_section
        )
    
    def _generate_report_body(self, report_data: dict) -> str:
        """Generate plain text body for daily report."""
        template = """
Network Monitor Daily Report - {date}

Summary:
- Total Devices: {total_devices}
- Total Pings: {total_pings}
- Total Speed Tests: {total_speed_tests}
- Alerts Generated: {alerts_generated}

Device Statistics:
{device_stats}

---
This is an automated daily report from Network Monitor.
        """.strip()
        
        device_stats = []
        for device in report_data.get('device_stats', []):
            stats = f"""
{device['device_name']} ({device['ip_address']}):
  - Uptime: {device['uptime_percentage']}%
  - Pings: {device['successful_pings']}/{device['total_pings']}
  - Avg Response: {device['avg_response_time']}ms
  - Speed Tests: {device['speed_tests']}
            """.strip()
            device_stats.append(stats)
        
        return template.format(
            date=report_data.get('date', 'Unknown'),
            total_devices=report_data.get('total_devices', 0),
            total_pings=report_data.get('total_pings', 0),
            total_speed_tests=report_data.get('total_speed_tests', 0),
            alerts_generated=report_data.get('alerts_generated', 0),
            device_stats='\n'.join(device_stats) if device_stats else 'No device data available'
        )
    
    def _generate_report_html_body(self, report_data: dict) -> str:
        """Generate HTML body for daily report."""
        # This would be a more complex HTML template
        # For now, return a simple version
        return f"<pre>{self._generate_report_body(report_data)}</pre>"
