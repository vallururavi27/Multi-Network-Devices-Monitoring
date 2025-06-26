#!/usr/bin/env python3
"""
Demo script to showcase all the enhanced network monitoring features
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device
from monitoring.models import PingResult, SpeedTestResult, TracerouteResult
from django.utils import timezone
import random

def create_demo_ping_results():
    """Create demo ping results for all devices"""
    print("📊 Creating demo ping results...")
    
    devices = Device.objects.all()
    
    for device in devices:
        # Create 10 recent ping results
        for i in range(10):
            timestamp = timezone.now() - timezone.timedelta(minutes=i*5)
            
            # Simulate realistic ping results
            if device.ip_address.startswith('192.168'):
                # Local devices - better performance
                is_reachable = random.choice([True] * 9 + [False])  # 90% uptime
                response_time = random.uniform(1.0, 5.0) if is_reachable else None
            else:
                # Internet devices - variable performance
                is_reachable = random.choice([True] * 8 + [False] * 2)  # 80% uptime
                response_time = random.uniform(10.0, 50.0) if is_reachable else None
            
            PingResult.objects.create(
                device=device,
                is_reachable=is_reachable,
                response_time=response_time,
                packet_loss=0.0 if is_reachable else 100.0,
                packets_sent=4,
                packets_received=4 if is_reachable else 0,
                timestamp=timestamp
            )
        
        # Update device current latency
        if device.current_latency:
            device.current_latency = random.uniform(
                device.current_latency * 0.8, 
                device.current_latency * 1.2
            )
            device.save()
        
        print(f"  ✅ Created ping results for {device.name}")

def create_demo_speed_results():
    """Create demo speed test results"""
    print("🚀 Creating demo speed test results...")
    
    devices = Device.objects.filter(ip_address__in=['8.8.8.8', '1.1.1.1', '192.168.1.1'])
    
    for device in devices:
        # Create 3 recent speed test results
        for i in range(3):
            timestamp = timezone.now() - timezone.timedelta(hours=i*8)
            
            # Simulate realistic speed test results
            if device.ip_address.startswith('192.168'):
                download_speed = random.uniform(90.0, 100.0)
                upload_speed = random.uniform(45.0, 50.0)
                ping_latency = random.uniform(1.0, 3.0)
            else:
                download_speed = random.uniform(70.0, 95.0)
                upload_speed = random.uniform(35.0, 45.0)
                ping_latency = random.uniform(10.0, 25.0)
            
            SpeedTestResult.objects.create(
                device=device,
                download_speed=download_speed,
                upload_speed=upload_speed,
                ping_latency=ping_latency,
                jitter=random.uniform(1.0, 5.0),
                packet_loss_percent=random.uniform(0.0, 2.0),
                server_name=f"Test Server {i+1}",
                server_location="Demo Location",
                test_duration=random.uniform(30.0, 60.0),
                is_successful=True,
                timestamp=timestamp
            )
        
        # Update device current speeds
        device.current_download_speed = random.uniform(
            device.current_download_speed * 0.9,
            device.current_download_speed * 1.1
        )
        device.current_upload_speed = random.uniform(
            device.current_upload_speed * 0.9,
            device.current_upload_speed * 1.1
        )
        device.save()
        
        print(f"  ✅ Created speed test results for {device.name}")

def create_demo_traceroute_results():
    """Create demo traceroute results"""
    print("🛣️  Creating demo traceroute results...")
    
    devices = Device.objects.filter(ip_address__in=['8.8.8.8', '1.1.1.1'])
    
    for device in devices:
        # Create sample traceroute hops
        hops = []
        for hop_num in range(1, random.randint(8, 15)):
            hops.append({
                'hop': hop_num,
                'ip': f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                'hostname': f"hop{hop_num}.example.com",
                'rtt1': random.uniform(5.0, 50.0),
                'rtt2': random.uniform(5.0, 50.0),
                'rtt3': random.uniform(5.0, 50.0),
            })
        
        TracerouteResult.objects.create(
            device=device,
            hops=hops,
            total_hops=len(hops),
            destination_reached=True,
            total_time=sum(hop['rtt1'] for hop in hops),
            is_successful=True,
            timestamp=timezone.now()
        )
        
        # Update device traceroute info
        device.traceroute_hops = hops
        device.last_traceroute = timezone.now()
        device.save()
        
        print(f"  ✅ Created traceroute results for {device.name}")

def update_device_statuses():
    """Update device statuses based on recent results"""
    print("🔄 Updating device statuses...")
    
    from devices.models import DeviceStatus
    
    devices = Device.objects.all()
    
    for device in devices:
        # Get latest ping result
        latest_ping = device.ping_results.first()
        
        if latest_ping:
            if latest_ping.is_reachable:
                if latest_ping.response_time and latest_ping.response_time > 100:
                    device.status = DeviceStatus.WARNING
                else:
                    device.status = DeviceStatus.ONLINE
                device.last_seen = latest_ping.timestamp
            else:
                device.status = DeviceStatus.OFFLINE
        else:
            device.status = DeviceStatus.UNKNOWN
        
        device.save()
        print(f"  ✅ Updated status for {device.name}: {device.get_status_display()}")

def main():
    """Main demo function"""
    print("🎯 Django Network Monitor - Feature Demo")
    print("=" * 60)
    
    try:
        # Create demo data
        create_demo_ping_results()
        print()
        
        create_demo_speed_results()
        print()
        
        create_demo_traceroute_results()
        print()
        
        update_device_statuses()
        print()
        
        print("🎉 Demo data creation completed!")
        print()
        print("🌟 Enhanced Features Now Available:")
        print("   ✅ Advanced filtering by IP, Host, Location, ISP")
        print("   ✅ Real-time latency, upload, and download speeds")
        print("   ✅ Traceroute functionality with hop analysis")
        print("   ✅ Geolocation information for devices")
        print("   ✅ Enhanced device actions (Ping, Speed Test, Traceroute)")
        print("   ✅ Professional table interface with sorting")
        print("   ✅ Real-time status updates")
        print("   ✅ Export functionality")
        print()
        print("📱 Access the enhanced interface:")
        print("   Device List: http://127.0.0.1:8000/devices/")
        print("   Dashboard:   http://127.0.0.1:8000/dashboard/")
        print("   Live Monitor: http://127.0.0.1:8000/dashboard/live/")
        print()
        print("🔧 Try these features:")
        print("   • Use the advanced filters to search by IP, location, ISP")
        print("   • Click the action buttons to run tests")
        print("   • Sort by different columns")
        print("   • Watch real-time updates")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
