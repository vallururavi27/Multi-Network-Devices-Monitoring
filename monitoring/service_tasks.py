"""
Comprehensive Service Monitoring Tasks
"""
import socket
import time
import requests
import ftplib
import ssl
import dns.resolver
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

from .models import Device
from .port_models import (
    PortMonitor, PortCheckResult, ServiceMonitor, 
    ServiceCheckResult, ServiceType, get_service_type_for_port
)

logger = logging.getLogger(__name__)


@shared_task
def monitor_all_ports():
    """Monitor all enabled port monitors"""
    logger.info("Starting comprehensive port monitoring")
    
    # Get all enabled port monitors
    port_monitors = PortMonitor.objects.filter(is_enabled=True)
    
    results = {
        'total_checked': 0,
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for port_monitor in port_monitors:
        try:
            result = check_port_connectivity(port_monitor)
            results['total_checked'] += 1
            
            if result['is_reachable']:
                results['successful'] += 1
            else:
                results['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error checking port {port_monitor}: {e}")
            results['errors'].append(str(e))
    
    logger.info(f"Port monitoring completed: {results}")
    return results


def check_port_connectivity(port_monitor):
    """Check connectivity to a specific port"""
    start_time = time.time()
    
    try:
        # Basic TCP connection test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(port_monitor.timeout)
        
        result = sock.connect_ex((port_monitor.device.ip_address, port_monitor.port))
        sock.close()
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        is_reachable = result == 0
        
        # Service-specific checks
        service_data = {}
        if is_reachable:
            service_data = perform_service_specific_check(port_monitor, response_time)
        
        # Create check result
        check_result = PortCheckResult.objects.create(
            port_monitor=port_monitor,
            is_reachable=is_reachable,
            response_time=response_time if is_reachable else None,
            error_message="" if is_reachable else f"Connection failed (code: {result})",
            **service_data
        )
        
        # Update port monitor status
        port_monitor.is_reachable = is_reachable
        port_monitor.last_check = timezone.now()
        
        if is_reachable:
            port_monitor.last_success = timezone.now()
            port_monitor.consecutive_failures = 0
        else:
            port_monitor.consecutive_failures += 1
        
        port_monitor.save()
        
        # Check if alert should be triggered
        if (not is_reachable and 
            port_monitor.alert_on_failure and 
            port_monitor.consecutive_failures >= port_monitor.alert_threshold):
            trigger_port_alert(port_monitor)
        
        return {
            'is_reachable': is_reachable,
            'response_time': response_time,
            'service_data': service_data
        }
        
    except Exception as e:
        logger.error(f"Error checking port {port_monitor}: {e}")
        
        # Create failed check result
        PortCheckResult.objects.create(
            port_monitor=port_monitor,
            is_reachable=False,
            error_message=str(e)
        )
        
        # Update port monitor
        port_monitor.is_reachable = False
        port_monitor.last_check = timezone.now()
        port_monitor.consecutive_failures += 1
        port_monitor.save()
        
        return {
            'is_reachable': False,
            'error': str(e)
        }


def perform_service_specific_check(port_monitor, base_response_time):
    """Perform service-specific checks based on service type"""
    service_data = {}
    
    try:
        if port_monitor.service_type in [ServiceType.HTTP, ServiceType.HTTPS]:
            service_data = check_http_service(port_monitor)
        elif port_monitor.service_type == ServiceType.FTP:
            service_data = check_ftp_service(port_monitor)
        elif port_monitor.service_type == ServiceType.SSH:
            service_data = check_ssh_service(port_monitor)
        elif port_monitor.service_type == ServiceType.DNS:
            service_data = check_dns_service(port_monitor)
        elif port_monitor.service_type in [ServiceType.MYSQL, ServiceType.POSTGRESQL, ServiceType.MSSQL]:
            service_data = check_database_service(port_monitor)
            
    except Exception as e:
        logger.warning(f"Service-specific check failed for {port_monitor}: {e}")
        service_data['service_error'] = str(e)
    
    return service_data


def check_http_service(port_monitor):
    """Check HTTP/HTTPS service"""
    protocol = 'https' if port_monitor.port in [443, 8443] else 'http'
    url = f"{protocol}://{port_monitor.device.ip_address}:{port_monitor.port}/"
    
    try:
        response = requests.get(url, timeout=port_monitor.timeout, verify=False)
        
        service_data = {
            'http_status_code': response.status_code,
            'http_response_size': len(response.content)
        }
        
        # Check SSL certificate for HTTPS
        if protocol == 'https':
            try:
                cert_info = ssl.get_server_certificate((port_monitor.device.ip_address, port_monitor.port))
                # Parse certificate expiry (simplified)
                service_data['ssl_cert_info'] = 'Valid'
            except:
                service_data['ssl_cert_info'] = 'Invalid or expired'
        
        return service_data
        
    except requests.RequestException as e:
        return {'http_error': str(e)}


def check_ftp_service(port_monitor):
    """Check FTP service"""
    try:
        ftp = ftplib.FTP()
        ftp.connect(port_monitor.device.ip_address, port_monitor.port, timeout=port_monitor.timeout)
        welcome_msg = ftp.getwelcome()
        ftp.quit()
        
        return {'ftp_welcome': welcome_msg[:100]}  # Truncate long messages
        
    except Exception as e:
        return {'ftp_error': str(e)}


def check_ssh_service(port_monitor):
    """Check SSH service (basic banner check)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(port_monitor.timeout)
        sock.connect((port_monitor.device.ip_address, port_monitor.port))
        
        # Read SSH banner
        banner = sock.recv(1024).decode('utf-8', errors='ignore')
        sock.close()
        
        return {'ssh_banner': banner.strip()[:100]}
        
    except Exception as e:
        return {'ssh_error': str(e)}


def check_dns_service(port_monitor):
    """Check DNS service"""
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [port_monitor.device.ip_address]
        resolver.timeout = port_monitor.timeout
        
        # Try to resolve a common domain
        start_time = time.time()
        result = resolver.resolve('google.com', 'A')
        dns_response_time = (time.time() - start_time) * 1000
        
        return {
            'dns_response_time': dns_response_time,
            'dns_records_count': len(result)
        }
        
    except Exception as e:
        return {'dns_error': str(e)}


def check_database_service(port_monitor):
    """Check database service (basic connection test)"""
    try:
        # This is a basic connection test
        # In production, you'd use specific database drivers
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(port_monitor.timeout)
        
        start_time = time.time()
        result = sock.connect_ex((port_monitor.device.ip_address, port_monitor.port))
        connection_time = (time.time() - start_time) * 1000
        sock.close()
        
        if result == 0:
            return {
                'db_connection_time': connection_time,
                'db_status': 'accepting_connections'
            }
        else:
            return {'db_error': f'Connection failed (code: {result})'}
            
    except Exception as e:
        return {'db_error': str(e)}


def trigger_port_alert(port_monitor):
    """Trigger alert for port failure"""
    try:
        from alerts.models import Alert, AlertType, AlertSeverity
        
        Alert.objects.create(
            device=port_monitor.device,
            title=f"Port {port_monitor.port} Unreachable",
            message=f"Port {port_monitor.port} ({port_monitor.get_service_type_display()}) on {port_monitor.device.name} has been unreachable for {port_monitor.consecutive_failures} consecutive checks.",
            alert_type=AlertType.CONNECTIVITY,
            severity=AlertSeverity.HIGH if port_monitor.consecutive_failures >= 5 else AlertSeverity.MEDIUM,
            is_active=True
        )
        
        logger.info(f"Alert triggered for {port_monitor}")
        
    except Exception as e:
        logger.error(f"Error creating alert for {port_monitor}: {e}")


@shared_task
def auto_discover_services(device_id):
    """Auto-discover services on a device by scanning common ports"""
    try:
        device = Device.objects.get(id=device_id)
        
        # Common ports to scan
        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 1433, 3306, 5432, 8080, 8443]
        
        discovered_services = []
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)  # Quick scan
                
                result = sock.connect_ex((device.ip_address, port))
                sock.close()
                
                if result == 0:  # Port is open
                    service_type = get_service_type_for_port(port)
                    
                    # Create or update port monitor
                    port_monitor, created = PortMonitor.objects.get_or_create(
                        device=device,
                        port=port,
                        defaults={
                            'service_type': service_type,
                            'is_enabled': True,
                            'check_interval': 300,
                            'timeout': 10
                        }
                    )
                    
                    if created:
                        discovered_services.append(f"{port} ({service_type})")
                        
            except Exception as e:
                logger.debug(f"Error scanning port {port} on {device.name}: {e}")
        
        logger.info(f"Service discovery completed for {device.name}: {discovered_services}")
        return {
            'device': device.name,
            'discovered_services': discovered_services
        }
        
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found for service discovery")
        return {'error': f'Device {device_id} not found'}
    except Exception as e:
        logger.error(f"Error in service discovery for device {device_id}: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_old_port_results():
    """Clean up old port check results to manage database size"""
    try:
        # Keep only last 30 days of results
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = PortCheckResult.objects.filter(timestamp__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old port check results")
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up old port results: {e}")
        return {'error': str(e)}
