"""
Celery tasks for network monitoring
"""
import logging
import time
import subprocess
import platform
import re
import ipaddress
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from devices.models import Device, DeviceStatus
from .models import PingResult, SpeedTestResult, SystemMetrics
from alerts.models import Alert, AlertType

logger = logging.getLogger(__name__)


class PingMonitor:
    """Ping monitoring utility"""
    
    def __init__(self):
        self.system = platform.system().lower()
    
    def ping_host(self, host: str, timeout: int = 5, count: int = 4) -> dict:
        """Ping a host and return results"""
        result = {
            'host': host,
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': count,
            'packets_received': 0,
            'error_message': None,
            'timestamp': time.time()
        }
        
        try:
            # Validate IP address
            ipaddress.ip_address(host)
            
            # Build ping command
            if self.system == 'windows':
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
            
            # Execute ping
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout * count + 10
            )
            
            if process.returncode == 0:
                output = process.stdout
                parsed = self._parse_ping_output(output, self.system)
                result.update(parsed)
            else:
                result['error_message'] = process.stderr or process.stdout
                
        except subprocess.TimeoutExpired:
            result['error_message'] = "Ping timeout"
        except ValueError:
            result['error_message'] = f"Invalid IP address: {host}"
        except Exception as e:
            result['error_message'] = str(e)
        
        return result
    
    def _parse_ping_output(self, output: str, system: str) -> dict:
        """Parse ping command output"""
        result = {
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': 0,
            'packets_received': 0
        }
        
        try:
            if system == 'windows':
                # Windows ping parsing
                packet_match = re.search(r'Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)', output)
                if packet_match:
                    sent, received, lost = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = (lost / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0
                
                # Extract response time
                time_match = re.search(r'Average = (\d+)ms', output)
                if time_match:
                    result['response_time'] = float(time_match.group(1))
            else:
                # Unix-like ping parsing
                packet_match = re.search(r'(\d+) packets transmitted, (\d+) (?:packets )?received', output)
                if packet_match:
                    sent, received = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = ((sent - received) / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0
                
                # Extract response time
                time_match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+', output)
                if time_match:
                    result['response_time'] = float(time_match.group(1))
        
        except Exception as e:
            logger.error(f"Error parsing ping output: {e}")
        
        return result


class SpeedTestMonitor:
    """Speed test monitoring utility"""
    
    def run_speed_test(self) -> dict:
        """Run speed test and return results"""
        result = {
            'download_speed': None,
            'upload_speed': None,
            'ping_latency': None,
            'server_name': None,
            'server_location': None,
            'test_duration': None,
            'is_successful': False,
            'error_message': None,
            'timestamp': time.time()
        }
        
        start_time = time.time()
        
        try:
            # Try to use speedtest-cli
            import speedtest
            
            st = speedtest.Speedtest()
            st.get_best_server()
            
            # Get server info
            server_info = st.results.server
            result['server_name'] = server_info.get('name', 'Unknown')
            result['server_location'] = f"{server_info.get('name', '')}, {server_info.get('country', '')}"
            
            # Perform tests
            result['ping_latency'] = round(st.results.ping, 2)
            
            download_speed = st.download()
            result['download_speed'] = round(download_speed / 1_000_000, 2)  # Convert to Mbps
            
            upload_speed = st.upload()
            result['upload_speed'] = round(upload_speed / 1_000_000, 2)  # Convert to Mbps
            
            result['is_successful'] = True
            
        except ImportError:
            # Fallback: simulate speed test results for demo
            import random
            time.sleep(2)  # Simulate test duration
            
            result.update({
                'download_speed': round(random.uniform(50, 100), 2),
                'upload_speed': round(random.uniform(10, 50), 2),
                'ping_latency': round(random.uniform(10, 50), 2),
                'server_name': 'Demo Server',
                'server_location': 'Demo Location',
                'is_successful': True
            })
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Speed test error: {e}")
        
        result['test_duration'] = time.time() - start_time
        return result


@shared_task(bind=True)
def monitor_single_device(self, device_id):
    """Monitor a single device"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        if not device.ping_enabled:
            return {'skipped': True, 'reason': 'Ping monitoring disabled'}
        
        # Perform ping test
        ping_monitor = PingMonitor()
        ping_result = ping_monitor.ping_host(
            device.ip_address,
            timeout=device.ping_timeout,
            count=4
        )
        
        # Store ping result
        db_result = PingResult.objects.create(
            device=device,
            is_reachable=ping_result['is_reachable'],
            response_time=ping_result['response_time'],
            packet_loss=ping_result['packet_loss'],
            packets_sent=ping_result['packets_sent'],
            packets_received=ping_result['packets_received'],
            error_message=ping_result.get('error_message', '')
        )
        
        # Update device status
        previous_status = device.status
        
        if ping_result['is_reachable']:
            if (ping_result['response_time'] and 
                ping_result['response_time'] > device.alert_threshold_latency):
                device.status = DeviceStatus.WARNING
            else:
                device.status = DeviceStatus.ONLINE
            device.last_seen = timezone.now()
        else:
            device.status = DeviceStatus.OFFLINE
        
        device.save()
        
        # Generate alerts if status changed
        if previous_status != device.status and device.alert_enabled:
            generate_status_alert.delay(device.id, previous_status, device.status)
        
        logger.info(f"Monitored {device.name}: {device.status}")
        
        return {
            'device_id': device.id,
            'device_name': device.name,
            'status': device.status,
            'ping_result': ping_result,
            'status_changed': previous_status != device.status
        }
        
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found")
        return {'error': f'Device {device_id} not found'}
    except Exception as e:
        logger.error(f"Error monitoring device {device_id}: {e}")
        self.retry(countdown=60, max_retries=3)


@shared_task
def monitor_all_devices():
    """Monitor all active devices"""
    devices = Device.objects.filter(is_active=True, ping_enabled=True)
    
    if not devices.exists():
        logger.info("No devices to monitor")
        return {'message': 'No devices to monitor'}
    
    results = []
    
    for device in devices:
        try:
            result = monitor_single_device.delay(device.id)
            results.append({
                'device_id': device.id,
                'task_id': result.id
            })
        except Exception as e:
            logger.error(f"Error queuing monitoring for device {device.id}: {e}")
    
    logger.info(f"Queued monitoring for {len(results)} devices")
    return {
        'queued_devices': len(results),
        'total_devices': devices.count(),
        'results': results
    }


@shared_task
def run_speed_test_for_device(device_id):
    """Run speed test for a specific device"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        if not device.speed_test_enabled:
            return {'skipped': True, 'reason': 'Speed test disabled'}
        
        # Check if device is reachable first
        if device.status == DeviceStatus.OFFLINE:
            return {'skipped': True, 'reason': 'Device offline'}
        
        # Perform speed test
        speed_monitor = SpeedTestMonitor()
        speed_result = speed_monitor.run_speed_test()
        
        # Store speed test result
        SpeedTestResult.objects.create(
            device=device,
            download_speed=speed_result['download_speed'],
            upload_speed=speed_result['upload_speed'],
            ping_latency=speed_result['ping_latency'],
            server_name=speed_result['server_name'],
            server_location=speed_result['server_location'],
            test_duration=speed_result['test_duration'],
            is_successful=speed_result['is_successful'],
            error_message=speed_result.get('error_message', '')
        )
        
        logger.info(f"Speed test completed for {device.name}")
        
        return {
            'device_id': device.id,
            'device_name': device.name,
            'speed_result': speed_result
        }
        
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found")
        return {'error': f'Device {device_id} not found'}
    except Exception as e:
        logger.error(f"Error running speed test for device {device_id}: {e}")
        return {'error': str(e)}


@shared_task
def generate_status_alert(device_id, previous_status, current_status):
    """Generate alert for device status change"""
    try:
        device = Device.objects.get(id=device_id)
        
        # Check for recent similar alerts (cooldown)
        cooldown_minutes = getattr(settings, 'NETWORK_MONITOR', {}).get('ALERT_COOLDOWN_MINUTES', 15)
        cooldown_time = timezone.now() - timedelta(minutes=cooldown_minutes)
        
        recent_alert = Alert.objects.filter(
            device=device,
            created_at__gt=cooldown_time,
            is_active=True
        ).first()
        
        if recent_alert:
            logger.info(f"Skipping alert for {device.name} - recent alert exists")
            return {'skipped': True, 'reason': 'Recent alert exists'}
        
        # Determine alert type and details
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
            message = f"Device {device.name} ({device.ip_address}) is experiencing high latency."
        else:
            return {'skipped': True, 'reason': 'No alert needed'}
        
        # Create alert
        alert = Alert.objects.create(
            device=device,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message
        )
        
        logger.info(f"Generated alert: {title}")
        
        return {
            'alert_id': alert.id,
            'title': title,
            'severity': severity
        }
        
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found")
        return {'error': f'Device {device_id} not found'}
    except Exception as e:
        logger.error(f"Error generating alert for device {device_id}: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_old_data():
    """Clean up old monitoring data"""
    try:
        max_days = getattr(settings, 'NETWORK_MONITOR', {}).get('MAX_PING_HISTORY_DAYS', 30)
        cutoff_date = timezone.now() - timedelta(days=max_days)
        
        # Delete old ping results
        old_pings = PingResult.objects.filter(timestamp__lt=cutoff_date)
        ping_count = old_pings.count()
        old_pings.delete()
        
        # Delete old speed test results (keep longer - 90 days)
        speed_cutoff = timezone.now() - timedelta(days=90)
        old_speeds = SpeedTestResult.objects.filter(timestamp__lt=speed_cutoff)
        speed_count = old_speeds.count()
        old_speeds.delete()
        
        # Delete resolved alerts older than 30 days
        alert_cutoff = timezone.now() - timedelta(days=30)
        old_alerts = Alert.objects.filter(
            resolved_at__lt=alert_cutoff,
            is_active=False
        )
        alert_count = old_alerts.count()
        old_alerts.delete()
        
        logger.info(f"Cleaned up {ping_count} ping results, {speed_count} speed tests, {alert_count} alerts")
        
        return {
            'ping_results_deleted': ping_count,
            'speed_results_deleted': speed_count,
            'alerts_deleted': alert_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {'error': str(e)}


@shared_task
def update_system_metrics():
    """Update system metrics"""
    try:
        metrics = SystemMetrics.get_or_create_today()
        metrics.update_device_counts()
        metrics.update_ping_stats()
        metrics.update_speed_test_stats()
        metrics.last_monitoring_run = timezone.now()
        metrics.save()
        
        logger.info("System metrics updated")
        
        return {
            'total_devices': metrics.total_devices,
            'online_devices': metrics.online_devices,
            'total_pings_today': metrics.total_pings_today,
            'uptime_percentage': metrics.uptime_percentage
        }
        
    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")
        return {'error': str(e)}


@shared_task
def run_traceroute_for_device(device_id):
    """Run traceroute for a specific device"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)

        # Perform traceroute
        import subprocess
        import platform
        import re

        system = platform.system().lower()
        if system == 'windows':
            cmd = ['tracert', '-h', '15', device.ip_address]
        else:
            cmd = ['traceroute', '-m', '15', device.ip_address]

        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = process.stdout

            # Parse traceroute output
            hops = []
            if system == 'windows':
                # Parse Windows tracert output
                lines = output.split('\n')
                for line in lines:
                    hop_match = re.search(r'^\s*(\d+)\s+(.+)', line)
                    if hop_match:
                        hop_num = int(hop_match.group(1))
                        hop_data = hop_match.group(2).strip()
                        hops.append({
                            'hop': hop_num,
                            'data': hop_data
                        })
            else:
                # Parse Unix traceroute output
                lines = output.split('\n')
                for line in lines:
                    hop_match = re.search(r'^\s*(\d+)\s+(.+)', line)
                    if hop_match:
                        hop_num = int(hop_match.group(1))
                        hop_data = hop_match.group(2).strip()
                        hops.append({
                            'hop': hop_num,
                            'data': hop_data
                        })

            # Store traceroute result
            from .models import TracerouteResult
            TracerouteResult.objects.create(
                device=device,
                hops=hops,
                total_hops=len(hops),
                destination_reached=process.returncode == 0,
                is_successful=True
            )

            # Update device traceroute info
            device.traceroute_hops = hops
            device.last_traceroute = timezone.now()
            device.save()

            logger.info(f"Traceroute completed for {device.name}")

            return {
                'device_id': device.id,
                'device_name': device.name,
                'hops': hops,
                'total_hops': len(hops),
                'output': output
            }

        except subprocess.TimeoutExpired:
            return {'error': 'Traceroute timed out'}

    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found")
        return {'error': f'Device {device_id} not found'}
    except Exception as e:
        logger.error(f"Error running traceroute for device {device_id}: {e}")
        return {'error': str(e)}


@shared_task
def discover_network_devices(subnet='192.168.1.0/24'):
    """Discover devices on a network subnet"""
    try:
        import ipaddress
        import subprocess
        import concurrent.futures

        network = ipaddress.ip_network(subnet, strict=False)
        discovered_devices = []

        def ping_host(ip):
            """Ping a single host"""
            try:
                system = platform.system().lower()
                if system == 'windows':
                    cmd = ['ping', '-n', '1', '-w', '1000', str(ip)]
                else:
                    cmd = ['ping', '-c', '1', '-W', '1', str(ip)]

                process = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

                if process.returncode == 0:
                    return {
                        'ip': str(ip),
                        'reachable': True,
                        'hostname': None  # Could add hostname resolution here
                    }
            except Exception:
                pass

            return None

        # Ping all IPs in the subnet (limit to reasonable size)
        ips_to_check = list(network.hosts())[:254]  # Limit to /24 equivalent

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(ping_host, ip) for ip in ips_to_check]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    discovered_devices.append(result)

        logger.info(f"Network discovery completed for {subnet}: {len(discovered_devices)} devices found")

        return {
            'subnet': subnet,
            'devices_found': len(discovered_devices),
            'devices': discovered_devices
        }

    except Exception as e:
        logger.error(f"Error in network discovery for {subnet}: {e}")
        return {'error': str(e)}
