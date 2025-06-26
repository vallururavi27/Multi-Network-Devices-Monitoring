#!/usr/bin/env python3
"""
Create sample data for Django Network Monitor
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device, DeviceType, DeviceStatus, DeviceGroup

def create_sample_devices():
    """Create sample devices for testing"""
    print("Creating sample devices...")
    
    # Sample devices data with enhanced information
    devices_data = [
        {
            'name': 'Google DNS Primary',
            'ip_address': '8.8.8.8',
            'hostname': 'dns.google',
            'description': 'Google Public DNS Server - Primary',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
            'country': 'United States',
            'city': 'Mountain View',
            'isp': 'Google LLC',
            'organization': 'Google',
            'current_latency': 15.2,
            'current_download_speed': 95.5,
            'current_upload_speed': 45.3,
            'ping_enabled': True,
            'alert_enabled': True,
        },
        {
            'name': 'Google DNS Secondary',
            'ip_address': '8.8.4.4',
            'hostname': 'dns.google',
            'description': 'Google Public DNS Server - Secondary',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
            'country': 'United States',
            'city': 'Mountain View',
            'isp': 'Google LLC',
            'organization': 'Google',
            'current_latency': 16.8,
            'current_download_speed': 92.1,
            'current_upload_speed': 43.7,
            'ping_enabled': True,
            'alert_enabled': True,
        },
        {
            'name': 'Cloudflare DNS',
            'ip_address': '1.1.1.1',
            'hostname': 'one.one.one.one',
            'description': 'Cloudflare Public DNS Server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
            'country': 'United States',
            'city': 'San Francisco',
            'isp': 'Cloudflare Inc',
            'organization': 'Cloudflare',
            'current_latency': 12.5,
            'current_download_speed': 98.2,
            'current_upload_speed': 47.9,
            'ping_enabled': True,
            'alert_enabled': True,
        },
        {
            'name': 'OpenDNS',
            'ip_address': '208.67.222.222',
            'hostname': 'resolver1.opendns.com',
            'description': 'OpenDNS Public Server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
            'country': 'United States',
            'city': 'San Francisco',
            'isp': 'Cisco OpenDNS',
            'organization': 'Cisco Systems',
            'current_latency': 18.3,
            'current_download_speed': 87.6,
            'current_upload_speed': 41.2,
            'ping_enabled': True,
            'alert_enabled': True,
        },
        {
            'name': 'Local Gateway',
            'ip_address': '192.168.1.1',
            'hostname': 'router.local',
            'description': 'Default local network gateway/router',
            'device_type': DeviceType.ROUTER,
            'location': 'Local Network',
            'country': 'Local',
            'city': 'Home',
            'isp': 'Local ISP',
            'organization': 'Home Network',
            'current_latency': 2.1,
            'current_download_speed': 100.0,
            'current_upload_speed': 50.0,
            'ping_enabled': True,
            'alert_enabled': True,
        },
        {
            'name': 'Local DNS',
            'ip_address': '192.168.1.2',
            'hostname': 'dns.local',
            'description': 'Local DNS server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Local Network',
            'country': 'Local',
            'city': 'Home',
            'isp': 'Local ISP',
            'organization': 'Home Network',
            'current_latency': 1.8,
            'current_download_speed': 100.0,
            'current_upload_speed': 50.0,
            'ping_enabled': True,
            'alert_enabled': True,
        }
    ]
    
    created_count = 0
    
    for device_data in devices_data:
        device, created = Device.objects.get_or_create(
            ip_address=device_data['ip_address'],
            defaults=device_data
        )
        
        if created:
            print(f"✅ Created device: {device.name} ({device.ip_address})")
            created_count += 1
        else:
            print(f"ℹ️  Device already exists: {device.name} ({device.ip_address})")
    
    print(f"\n📊 Summary: {created_count} new devices created")
    return created_count

def create_sample_groups():
    """Create sample device groups"""
    print("\nCreating sample device groups...")
    
    # Create groups
    internet_group, created = DeviceGroup.objects.get_or_create(
        name='Internet Services',
        defaults={
            'description': 'Public internet services and DNS servers',
            'color': '#007bff'
        }
    )
    
    local_group, created = DeviceGroup.objects.get_or_create(
        name='Local Network',
        defaults={
            'description': 'Local network devices and infrastructure',
            'color': '#28a745'
        }
    )
    
    # Add devices to groups
    internet_devices = Device.objects.filter(location='Internet')
    local_devices = Device.objects.filter(location='Local Network')
    
    internet_group.devices.set(internet_devices)
    local_group.devices.set(local_devices)
    
    print(f"✅ Created group: {internet_group.name} ({internet_devices.count()} devices)")
    print(f"✅ Created group: {local_group.name} ({local_devices.count()} devices)")

def main():
    """Main function"""
    print("🚀 Creating Sample Data for Django Network Monitor")
    print("=" * 60)
    
    try:
        # Create sample devices
        device_count = create_sample_devices()
        
        # Create sample groups
        create_sample_groups()
        
        print("\n🎉 Sample data creation completed!")
        print(f"📱 You can now access the application:")
        print(f"   Web Interface: http://127.0.0.1:8000")
        print(f"   Admin Panel:   http://127.0.0.1:8000/admin/")
        print(f"   Username: admin")
        print(f"   Password: admin")
        
        if device_count > 0:
            print(f"\n💡 Next steps:")
            print(f"   1. Start Redis: redis-server")
            print(f"   2. Start Celery worker: celery -A network_monitor worker --loglevel=info")
            print(f"   3. Start Celery beat: celery -A network_monitor beat --loglevel=info")
            print(f"   4. Start Django server: python manage.py runserver")
            print(f"   5. The monitoring will start automatically!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
