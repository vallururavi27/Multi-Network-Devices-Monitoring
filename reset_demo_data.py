#!/usr/bin/env python3
"""
Reset and create clean demo data with just 3-4 devices
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device, DeviceType, DeviceStatus
from monitoring.models import PingResult, SpeedTestResult, TracerouteResult
from alerts.models import Alert


def clear_all_data():
    """Clear all existing data"""
    print("🧹 Clearing all existing data...")
    
    # Clear all devices and related data
    Device.objects.all().delete()
    print("✅ Cleared all devices")
    
    # Clear monitoring results
    PingResult.objects.all().delete()
    SpeedTestResult.objects.all().delete()
    TracerouteResult.objects.all().delete()
    print("✅ Cleared all monitoring results")
    
    # Clear alerts
    Alert.objects.all().delete()
    print("✅ Cleared all alerts")


def create_demo_devices():
    """Create 4 clean demo devices"""
    print("\n📱 Creating demo devices...")
    
    demo_devices = [
        {
            'name': 'Google DNS Primary',
            'ip_address': '8.8.8.8',
            'hostname': 'dns.google',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Mountain View, CA',
            'city': 'Mountain View',
            'country': 'United States',
            'isp': 'Google LLC',
            'organization': 'Google LLC',
            'latitude': Decimal('37.4056'),
            'longitude': Decimal('-122.0775'),
            'status': DeviceStatus.ONLINE,
            'current_latency': 15.2,
            'description': 'Google Public DNS - Primary server'
        },
        {
            'name': 'Cloudflare DNS',
            'ip_address': '1.1.1.1',
            'hostname': 'one.one.one.one',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'San Francisco, CA',
            'city': 'San Francisco',
            'country': 'United States',
            'isp': 'Cloudflare Inc',
            'organization': 'Cloudflare Inc',
            'latitude': Decimal('37.7749'),
            'longitude': Decimal('-122.4194'),
            'status': DeviceStatus.ONLINE,
            'current_latency': 12.8,
            'description': 'Cloudflare Public DNS - Fast and secure'
        },
        {
            'name': 'OpenDNS Resolver',
            'ip_address': '208.67.222.222',
            'hostname': 'resolver1.opendns.com',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'San Francisco, CA',
            'city': 'San Francisco',
            'country': 'United States',
            'isp': 'Cisco OpenDNS',
            'organization': 'Cisco Systems Inc',
            'latitude': Decimal('37.7849'),
            'longitude': Decimal('-122.4094'),
            'status': DeviceStatus.WARNING,
            'current_latency': 45.6,
            'description': 'OpenDNS Public Resolver - Family safe DNS'
        },
        {
            'name': 'Quad9 DNS',
            'ip_address': '9.9.9.9',
            'hostname': 'dns.quad9.net',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Berkeley, CA',
            'city': 'Berkeley',
            'country': 'United States',
            'isp': 'Quad9',
            'organization': 'Quad9 Foundation',
            'latitude': Decimal('37.8715'),
            'longitude': Decimal('-122.2730'),
            'status': DeviceStatus.ONLINE,
            'current_latency': 18.4,
            'description': 'Quad9 Secure DNS - Malware blocking DNS'
        }
    ]
    
    created_devices = []
    
    for device_data in demo_devices:
        device = Device.objects.create(
            name=device_data['name'],
            ip_address=device_data['ip_address'],
            hostname=device_data['hostname'],
            device_type=device_data['device_type'],
            location=device_data['location'],
            city=device_data['city'],
            country=device_data['country'],
            isp=device_data['isp'],
            organization=device_data['organization'],
            latitude=device_data['latitude'],
            longitude=device_data['longitude'],
            status=device_data['status'],
            current_latency=device_data['current_latency'],
            description=device_data['description'],
            ping_enabled=True,
            alert_enabled=True,
            is_active=True,
        )
        
        created_devices.append(device)
        print(f"✅ Created: {device.name} ({device.ip_address})")
    
    return created_devices


def create_sample_monitoring_data(devices):
    """Create some sample monitoring data"""
    print("\n📊 Creating sample monitoring data...")
    
    from django.utils import timezone
    from datetime import timedelta
    import random
    
    # Create ping results for the last 24 hours
    for device in devices:
        for hour in range(24):
            timestamp = timezone.now() - timedelta(hours=hour)
            
            # Simulate different response patterns
            if device.status == DeviceStatus.ONLINE:
                is_reachable = random.choice([True] * 9 + [False])  # 90% success
                response_time = random.uniform(10.0, 30.0)
            elif device.status == DeviceStatus.WARNING:
                is_reachable = random.choice([True] * 7 + [False] * 3)  # 70% success
                response_time = random.uniform(30.0, 80.0)
            else:
                is_reachable = random.choice([True] * 3 + [False] * 7)  # 30% success
                response_time = random.uniform(80.0, 200.0)
            
            PingResult.objects.create(
                device=device,
                is_reachable=is_reachable,
                response_time=response_time if is_reachable else None,
                packet_loss=0.0 if is_reachable else 100.0,
                packets_sent=4,
                packets_received=4 if is_reachable else 0,
                timestamp=timestamp
            )
    
    print(f"✅ Created ping results for {len(devices)} devices")
    
    # Create a few speed test results
    for device in devices[:2]:  # Only for first 2 devices
        for day in range(3):
            timestamp = timezone.now() - timedelta(days=day, hours=random.randint(0, 23))
            
            SpeedTestResult.objects.create(
                device=device,
                download_speed=random.uniform(100.0, 1000.0),
                upload_speed=random.uniform(50.0, 200.0),
                ping_latency=random.uniform(10.0, 30.0),
                jitter=random.uniform(1.0, 5.0),
                packet_loss_percent=random.uniform(0.0, 1.0),
                server_name=f"Test Server {random.randint(1, 3)}",
                server_location=random.choice(["New York", "Los Angeles", "Chicago"]),
                test_duration=random.uniform(30.0, 60.0),
                is_successful=True,
                timestamp=timestamp
            )
    
    print("✅ Created speed test results")


def main():
    """Main function"""
    print("🎯 Network Monitor - Demo Data Reset")
    print("=" * 50)
    print("This will:")
    print("1. Clear ALL existing devices and data")
    print("2. Create 4 clean demo devices")
    print("3. Add sample monitoring data")
    print("=" * 50)
    
    confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return
    
    try:
        # Clear all data
        clear_all_data()
        
        # Create demo devices
        devices = create_demo_devices()
        
        # Create sample monitoring data
        create_sample_monitoring_data(devices)
        
        print(f"\n🎉 Demo data reset completed!")
        print(f"📊 Created {len(devices)} demo devices")
        print(f"🌐 Access your network monitor: http://127.0.0.1:8000/")
        print(f"📱 Dashboard: http://127.0.0.1:8000/dashboard/")
        print(f"🗺️  Device Map: http://127.0.0.1:8000/devices/map/")
        print(f"📋 Device List: http://127.0.0.1:8000/devices/")
        
        print(f"\n📍 Demo Devices Created:")
        for device in devices:
            print(f"   • {device.name} ({device.ip_address}) - {device.get_status_display()}")
        
        print(f"\n💡 Features to test:")
        print(f"   ✅ Interactive map with device locations")
        print(f"   ✅ Real-time dashboard with statistics")
        print(f"   ✅ Device filtering and search")
        print(f"   ✅ Ping and monitoring tests")
        print(f"   ✅ Import functionality for your data")
        print(f"   ✅ Donation support options")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
