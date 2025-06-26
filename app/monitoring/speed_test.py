"""
Speed test functionality for network monitoring
"""
import time
import logging
import speedtest
from typing import Dict, Optional, List
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)

class SpeedTestMonitor:
    """Handles network speed testing operations."""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def run_speed_test(self, server_id: Optional[int] = None, timeout: int = 120) -> Dict:
        """
        Run a comprehensive speed test.
        
        Args:
            server_id: Specific server ID to use (optional)
            timeout: Maximum time to wait for test completion
            
        Returns:
            Dictionary with speed test results
        """
        result = {
            'download_speed': None,
            'upload_speed': None,
            'ping_latency': None,
            'server_name': None,
            'server_location': None,
            'server_country': None,
            'server_sponsor': None,
            'server_id': None,
            'test_duration': None,
            'is_successful': False,
            'error_message': None,
            'timestamp': time.time(),
            'client_ip': None,
            'client_isp': None
        }
        
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._perform_speed_test, server_id)
                test_result = future.result(timeout=timeout)
                result.update(test_result)
                result['is_successful'] = True
                
        except TimeoutError:
            result['error_message'] = f"Speed test timed out after {timeout} seconds"
            logger.error(f"Speed test timeout: {timeout}s")
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Speed test error: {str(e)}")
        
        result['test_duration'] = time.time() - start_time
        return result
    
    def _perform_speed_test(self, server_id: Optional[int] = None) -> Dict:
        """
        Perform the actual speed test.
        
        Args:
            server_id: Specific server ID to use
            
        Returns:
            Dictionary with test results
        """
        st = speedtest.Speedtest()
        
        # Get client configuration
        config = st.get_config()
        client_info = {
            'client_ip': config.get('client', {}).get('ip'),
            'client_isp': config.get('client', {}).get('isp')
        }
        
        # Get server list and select best server
        if server_id:
            servers = st.get_servers([server_id])
            if not servers or server_id not in servers:
                raise Exception(f"Server ID {server_id} not found")
            st.get_best_server(servers[server_id])
        else:
            st.get_best_server()
        
        server_info = st.results.server
        
        # Perform ping test
        ping_result = st.results.ping
        
        # Perform download test
        download_speed = st.download()
        
        # Perform upload test
        upload_speed = st.upload()
        
        return {
            'download_speed': round(download_speed / 1_000_000, 2),  # Convert to Mbps
            'upload_speed': round(upload_speed / 1_000_000, 2),     # Convert to Mbps
            'ping_latency': round(ping_result, 2),
            'server_name': server_info.get('name'),
            'server_location': f"{server_info.get('name')}, {server_info.get('country')}",
            'server_country': server_info.get('country'),
            'server_sponsor': server_info.get('sponsor'),
            'server_id': server_info.get('id'),
            **client_info
        }
    
    def get_available_servers(self, limit: int = 10) -> List[Dict]:
        """
        Get list of available speed test servers.
        
        Args:
            limit: Maximum number of servers to return
            
        Returns:
            List of server information dictionaries
        """
        servers = []
        
        try:
            st = speedtest.Speedtest()
            server_list = st.get_servers()
            
            # Flatten server list and sort by distance
            all_servers = []
            for server_group in server_list.values():
                all_servers.extend(server_group)
            
            # Sort by distance and take top servers
            all_servers.sort(key=lambda x: x.get('d', float('inf')))
            
            for server in all_servers[:limit]:
                servers.append({
                    'id': server.get('id'),
                    'name': server.get('name'),
                    'sponsor': server.get('sponsor'),
                    'country': server.get('country'),
                    'cc': server.get('cc'),
                    'distance': round(server.get('d', 0), 2),
                    'latency': server.get('latency'),
                    'url': server.get('url')
                })
                
        except Exception as e:
            logger.error(f"Error getting server list: {str(e)}")
        
        return servers
    
    def test_server_latency(self, server_id: int, timeout: int = 30) -> Optional[float]:
        """
        Test latency to a specific server.
        
        Args:
            server_id: Server ID to test
            timeout: Timeout in seconds
            
        Returns:
            Latency in milliseconds or None if failed
        """
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._test_latency, server_id)
                return future.result(timeout=timeout)
        except Exception as e:
            logger.error(f"Latency test error for server {server_id}: {str(e)}")
            return None
    
    def _test_latency(self, server_id: int) -> float:
        """
        Perform latency test to specific server.
        
        Args:
            server_id: Server ID to test
            
        Returns:
            Latency in milliseconds
        """
        st = speedtest.Speedtest()
        servers = st.get_servers([server_id])
        
        if not servers or server_id not in servers:
            raise Exception(f"Server ID {server_id} not found")
        
        st.get_best_server(servers[server_id])
        return st.results.ping
    
    def quick_speed_test(self, timeout: int = 60) -> Dict:
        """
        Run a quick speed test (download only).
        
        Args:
            timeout: Maximum time to wait for test completion
            
        Returns:
            Dictionary with quick test results
        """
        result = {
            'download_speed': None,
            'ping_latency': None,
            'server_name': None,
            'test_duration': None,
            'is_successful': False,
            'error_message': None,
            'timestamp': time.time()
        }
        
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._quick_test)
                test_result = future.result(timeout=timeout)
                result.update(test_result)
                result['is_successful'] = True
                
        except TimeoutError:
            result['error_message'] = f"Quick speed test timed out after {timeout} seconds"
        except Exception as e:
            result['error_message'] = str(e)
        
        result['test_duration'] = time.time() - start_time
        return result
    
    def _quick_test(self) -> Dict:
        """
        Perform quick download speed test.
        
        Returns:
            Dictionary with quick test results
        """
        st = speedtest.Speedtest()
        st.get_best_server()
        
        server_info = st.results.server
        ping_result = st.results.ping
        download_speed = st.download()
        
        return {
            'download_speed': round(download_speed / 1_000_000, 2),
            'ping_latency': round(ping_result, 2),
            'server_name': server_info.get('name')
        }
