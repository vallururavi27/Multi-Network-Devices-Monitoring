"""
Main monitoring engine that coordinates ping and speed tests
"""
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from app import db
from app.models import Device, PingResult, SpeedTestResult, DeviceStatus, Alert, AlertType
from app.monitoring.ping import PingMonitor
from app.monitoring.speed_test import SpeedTestMonitor

logger = logging.getLogger(__name__)

class NetworkMonitor:
    """Main network monitoring engine."""
    
    def __init__(self, max_workers: int = 10):
        self.ping_monitor = PingMonitor()
        self.speed_monitor = SpeedTestMonitor()
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self._running = False
    
    def monitor_device(self, device: Device) -> Dict:
        """
        Monitor a single device (ping and optionally speed test).
        
        Args:
            device: Device object to monitor
            
        Returns:
            Dictionary with monitoring results
        """
        results = {
            'device_id': device.id,
            'device_name': device.name,
            'ip_address': device.ip_address,
            'timestamp': datetime.utcnow(),
            'ping_result': None,
            'speed_result': None,
            'status_changed': False,
            'previous_status': device.status,
            'current_status': device.status
        }
        
        try:
            # Perform ping test if enabled
            if device.ping_enabled:
                ping_result = self._ping_device(device)
                results['ping_result'] = ping_result
                
                # Update device status based on ping result
                new_status = self._determine_device_status(ping_result, device)
                if new_status != device.status:
                    results['status_changed'] = True
                    results['previous_status'] = device.status
                    results['current_status'] = new_status
                    
                    # Update device in database
                    device.status = new_status
                    if ping_result['is_reachable']:
                        device.last_seen = datetime.utcnow()
                    
                    db.session.commit()
            
            # Perform speed test if enabled and device is reachable
            if (device.speed_test_enabled and 
                results['ping_result'] and 
                results['ping_result']['is_reachable']):
                
                # Check if it's time for a speed test
                if self._should_run_speed_test(device):
                    speed_result = self._speed_test_device(device)
                    results['speed_result'] = speed_result
            
        except Exception as e:
            logger.error(f"Error monitoring device {device.name}: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def monitor_devices(self, device_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Monitor multiple devices concurrently.
        
        Args:
            device_ids: List of device IDs to monitor (None for all active devices)
            
        Returns:
            List of monitoring results
        """
        # Get devices to monitor
        query = Device.query.filter_by(is_active=True)
        if device_ids:
            query = query.filter(Device.id.in_(device_ids))
        
        devices = query.all()
        
        if not devices:
            logger.info("No devices to monitor")
            return []
        
        logger.info(f"Starting monitoring for {len(devices)} devices")
        
        results = []
        
        # Monitor devices concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit monitoring tasks
            future_to_device = {
                executor.submit(self.monitor_device, device): device 
                for device in devices
            }
            
            # Collect results
            for future in as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout per device
                    results.append(result)
                    
                    # Generate alerts if status changed
                    if result.get('status_changed'):
                        self._generate_status_alert(device, result)
                        
                except Exception as e:
                    logger.error(f"Error monitoring device {device.name}: {str(e)}")
                    results.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'error': str(e),
                        'timestamp': datetime.utcnow()
                    })
        
        logger.info(f"Completed monitoring for {len(devices)} devices")
        return results
    
    def _ping_device(self, device: Device) -> Dict:
        """
        Ping a device and store results.
        
        Args:
            device: Device to ping
            
        Returns:
            Dictionary with ping results
        """
        ping_result = self.ping_monitor.ping_host(
            device.ip_address,
            timeout=device.ping_timeout,
            count=4
        )
        
        # Store ping result in database
        db_result = PingResult(
            device_id=device.id,
            is_reachable=ping_result['is_reachable'],
            response_time=ping_result['response_time'],
            packet_loss=ping_result['packet_loss'],
            error_message=ping_result.get('error_message')
        )
        
        db.session.add(db_result)
        db.session.commit()
        
        return ping_result
    
    def _speed_test_device(self, device: Device) -> Dict:
        """
        Run speed test for a device and store results.
        
        Args:
            device: Device to test
            
        Returns:
            Dictionary with speed test results
        """
        speed_result = self.speed_monitor.run_speed_test(timeout=120)
        
        # Store speed test result in database
        db_result = SpeedTestResult(
            device_id=device.id,
            download_speed=speed_result['download_speed'],
            upload_speed=speed_result['upload_speed'],
            ping_latency=speed_result['ping_latency'],
            server_name=speed_result['server_name'],
            server_location=speed_result['server_location'],
            test_duration=speed_result['test_duration'],
            error_message=speed_result.get('error_message'),
            is_successful=speed_result['is_successful']
        )
        
        db.session.add(db_result)
        db.session.commit()
        
        return speed_result
    
    def _determine_device_status(self, ping_result: Dict, device: Device) -> DeviceStatus:
        """
        Determine device status based on ping results.
        
        Args:
            ping_result: Ping test results
            device: Device being monitored
            
        Returns:
            DeviceStatus enum value
        """
        if not ping_result['is_reachable']:
            return DeviceStatus.OFFLINE
        
        # Check for high latency warning
        if (ping_result['response_time'] and 
            ping_result['response_time'] > device.alert_threshold_latency):
            return DeviceStatus.WARNING
        
        # Check for high packet loss warning
        if ping_result['packet_loss'] > device.alert_threshold_packet_loss:
            return DeviceStatus.WARNING
        
        return DeviceStatus.ONLINE
    
    def _should_run_speed_test(self, device: Device) -> bool:
        """
        Check if it's time to run a speed test for the device.
        
        Args:
            device: Device to check
            
        Returns:
            True if speed test should be run
        """
        if not device.speed_test_enabled:
            return False
        
        # Get last speed test result
        last_result = SpeedTestResult.query.filter_by(device_id=device.id)\
            .order_by(SpeedTestResult.timestamp.desc()).first()
        
        if not last_result:
            return True  # No previous test, run one
        
        # Check if enough time has passed
        time_since_last = datetime.utcnow() - last_result.timestamp
        return time_since_last.total_seconds() >= device.speed_test_interval
    
    def _generate_status_alert(self, device: Device, result: Dict):
        """
        Generate alert for device status change.
        
        Args:
            device: Device that changed status
            result: Monitoring result
        """
        if not device.alert_enabled:
            return
        
        previous_status = result['previous_status']
        current_status = result['current_status']
        
        # Determine alert type
        if current_status == DeviceStatus.OFFLINE:
            alert_type = AlertType.DEVICE_DOWN
            severity = 'high'
            title = f"Device {device.name} is DOWN"
            message = f"Device {device.name} ({device.ip_address}) is no longer reachable."
        elif current_status == DeviceStatus.ONLINE and previous_status == DeviceStatus.OFFLINE:
            alert_type = AlertType.DEVICE_UP
            severity = 'medium'
            title = f"Device {device.name} is UP"
            message = f"Device {device.name} ({device.ip_address}) is now reachable again."
        elif current_status == DeviceStatus.WARNING:
            alert_type = AlertType.HIGH_LATENCY
            severity = 'medium'
            title = f"Device {device.name} has performance issues"
            message = f"Device {device.name} ({device.ip_address}) is experiencing high latency or packet loss."
        else:
            return  # No alert needed
        
        # Check for recent similar alerts (cooldown)
        cooldown_time = datetime.utcnow() - timedelta(minutes=15)  # 15 minute cooldown
        recent_alert = Alert.query.filter(
            Alert.device_id == device.id,
            Alert.alert_type == alert_type,
            Alert.created_at > cooldown_time,
            Alert.is_active == True
        ).first()
        
        if recent_alert:
            logger.info(f"Skipping alert for {device.name} - recent alert exists")
            return
        
        # Create new alert
        alert = Alert(
            device_id=device.id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message
        )
        
        db.session.add(alert)
        db.session.commit()
        
        logger.info(f"Generated alert: {title}")
    
    def get_device_status_summary(self) -> Dict:
        """
        Get summary of all device statuses.
        
        Returns:
            Dictionary with status counts
        """
        devices = Device.query.filter_by(is_active=True).all()
        
        summary = {
            'total': len(devices),
            'online': 0,
            'offline': 0,
            'warning': 0,
            'unknown': 0
        }
        
        for device in devices:
            if device.status == DeviceStatus.ONLINE:
                summary['online'] += 1
            elif device.status == DeviceStatus.OFFLINE:
                summary['offline'] += 1
            elif device.status == DeviceStatus.WARNING:
                summary['warning'] += 1
            else:
                summary['unknown'] += 1
        
        return summary
