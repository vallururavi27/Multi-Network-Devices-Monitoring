"""
Ping monitoring functionality
"""
import time
import socket
import subprocess
import platform
import re
from typing import Dict, Optional, Tuple
from ping3 import ping, verbose_ping
import logging

logger = logging.getLogger(__name__)

class PingMonitor:
    """Handles ping operations for network monitoring."""
    
    def __init__(self):
        self.system = platform.system().lower()
    
    def ping_host(self, host: str, timeout: int = 5, count: int = 4) -> Dict:
        """
        Ping a host and return detailed results.
        
        Args:
            host: IP address or hostname to ping
            timeout: Timeout in seconds
            count: Number of ping packets to send
            
        Returns:
            Dictionary with ping results
        """
        result = {
            'host': host,
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': count,
            'packets_received': 0,
            'min_time': None,
            'max_time': None,
            'avg_time': None,
            'error_message': None,
            'timestamp': time.time()
        }
        
        try:
            # First try with ping3 library for simple ping
            response_time = ping(host, timeout=timeout)
            
            if response_time is not None:
                result['is_reachable'] = True
                result['response_time'] = response_time * 1000  # Convert to milliseconds
                result['packet_loss'] = 0.0
                result['packets_received'] = 1
                result['min_time'] = result['max_time'] = result['avg_time'] = result['response_time']
            else:
                # If ping3 fails, try system ping for more detailed results
                detailed_result = self._system_ping(host, timeout, count)
                result.update(detailed_result)
                
        except Exception as e:
            logger.error(f"Ping error for {host}: {str(e)}")
            result['error_message'] = str(e)
        
        return result
    
    def _system_ping(self, host: str, timeout: int, count: int) -> Dict:
        """
        Use system ping command for detailed results.
        
        Args:
            host: IP address or hostname to ping
            timeout: Timeout in seconds
            count: Number of ping packets to send
            
        Returns:
            Dictionary with detailed ping results
        """
        result = {
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': count,
            'packets_received': 0,
            'min_time': None,
            'max_time': None,
            'avg_time': None,
            'error_message': None
        }
        
        try:
            # Build ping command based on operating system
            if self.system == 'windows':
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
            
            # Execute ping command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 10  # Extra time for command execution
            )
            
            if process.returncode == 0:
                # Parse successful ping output
                output = process.stdout
                parsed = self._parse_ping_output(output, self.system)
                result.update(parsed)
            else:
                # Parse error output
                error_output = process.stderr or process.stdout
                result['error_message'] = error_output.strip()
                
        except subprocess.TimeoutExpired:
            result['error_message'] = f"Ping command timed out after {timeout * count + 10} seconds"
        except Exception as e:
            result['error_message'] = f"System ping failed: {str(e)}"
        
        return result
    
    def _parse_ping_output(self, output: str, system: str) -> Dict:
        """
        Parse ping command output to extract statistics.
        
        Args:
            output: Raw ping command output
            system: Operating system (windows/linux/darwin)
            
        Returns:
            Dictionary with parsed ping statistics
        """
        result = {
            'is_reachable': False,
            'response_time': None,
            'packet_loss': 100.0,
            'packets_sent': 0,
            'packets_received': 0,
            'min_time': None,
            'max_time': None,
            'avg_time': None
        }
        
        try:
            if system == 'windows':
                # Parse Windows ping output
                # Look for packet statistics
                packet_match = re.search(r'Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)', output)
                if packet_match:
                    sent, received, lost = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = (lost / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0
                
                # Look for timing statistics
                time_match = re.search(r'Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms', output)
                if time_match:
                    min_time, max_time, avg_time = map(int, time_match.groups())
                    result['min_time'] = min_time
                    result['max_time'] = max_time
                    result['avg_time'] = avg_time
                    result['response_time'] = avg_time
            
            else:
                # Parse Unix-like ping output
                # Look for packet statistics
                packet_match = re.search(r'(\d+) packets transmitted, (\d+) (?:packets )?received', output)
                if packet_match:
                    sent, received = map(int, packet_match.groups())
                    result['packets_sent'] = sent
                    result['packets_received'] = received
                    result['packet_loss'] = ((sent - received) / sent) * 100 if sent > 0 else 100.0
                    result['is_reachable'] = received > 0
                
                # Look for timing statistics
                time_match = re.search(r'min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', output)
                if time_match:
                    min_time, avg_time, max_time, mdev = map(float, time_match.groups())
                    result['min_time'] = min_time
                    result['max_time'] = max_time
                    result['avg_time'] = avg_time
                    result['response_time'] = avg_time
        
        except Exception as e:
            logger.error(f"Error parsing ping output: {str(e)}")
        
        return result
    
    def is_host_reachable(self, host: str, timeout: int = 3) -> bool:
        """
        Quick check if host is reachable.
        
        Args:
            host: IP address or hostname
            timeout: Timeout in seconds
            
        Returns:
            True if host is reachable, False otherwise
        """
        try:
            response_time = ping(host, timeout=timeout)
            return response_time is not None
        except Exception:
            return False
    
    def resolve_hostname(self, hostname: str, timeout: int = 5) -> Optional[str]:
        """
        Resolve hostname to IP address.
        
        Args:
            hostname: Hostname to resolve
            timeout: Timeout in seconds
            
        Returns:
            IP address string or None if resolution fails
        """
        try:
            socket.setdefaulttimeout(timeout)
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except socket.gaierror:
            return None
        except Exception as e:
            logger.error(f"Hostname resolution error for {hostname}: {str(e)}")
            return None
        finally:
            socket.setdefaulttimeout(None)
