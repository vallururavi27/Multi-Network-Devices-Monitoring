#!/usr/bin/env python3
"""
Update existing sample data with enhanced information
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device, DeviceType

def update_existing_devices():
    """Update existing devices with enhanced information"""
    print("Updating existing devices with enhanced data...")
    
    # Enhanced device data
    device_updates = {
        '8.8.8.8': {
            'hostname': 'dns.google',
            'country': 'United States',
            'city': 'Mountain View',
            'isp': 'Google LLC',
            'organization': 'Google',
            'current_latency': 15.2,
            'current_download_speed': 95.5,
            'current_upload_speed': 45.3,
        },
        '8.8.4.4': {
            'hostname': 'dns.google',
            'country': 'United States',
            'city': 'Mountain View',
            'isp': 'Google LLC',
            'organization': 'Google',
            'current_latency': 16.8,
            'current_download_speed': 92.1,
            'current_upload_speed': 43.7,
        },
        '1.1.1.1': {
            'hostname': 'one.one.one.one',
            'country': 'United States',
            'city': 'San Francisco',
            'isp': 'Cloudflare Inc',
            'organization': 'Cloudflare',
            'current_latency': 12.5,
            'current_download_speed': 98.2,
            'current_upload_speed': 47.9,
        },
        '208.67.222.222': {
            'hostname': 'resolver1.opendns.com',
            'country': 'United States',
            'city': 'San Francisco',
            'isp': 'Cisco OpenDNS',
            'organization': 'Cisco Systems',
            'current_latency': 18.3,
            'current_download_speed': 87.6,
            'current_upload_speed': 41.2,
        },
        '192.168.1.1': {
            'hostname': 'router.local',
            'country': 'Local',
            'city': 'Home',
            'isp': 'Local ISP',
            'organization': 'Home Network',
            'current_latency': 2.1,
            'current_download_speed': 100.0,
            'current_upload_speed': 50.0,
        },
        '192.168.1.2': {
            'hostname': 'dns.local',
            'country': 'Local',
            'city': 'Home',
            'isp': 'Local ISP',
            'organization': 'Home Network',
            'current_latency': 1.8,
            'current_download_speed': 100.0,
            'current_upload_speed': 50.0,
        }
    }
    
    updated_count = 0
    
    for ip_address, update_data in device_updates.items():
        try:
            device = Device.objects.get(ip_address=ip_address)
            
            # Update device fields
            for field, value in update_data.items():
                setattr(device, field, value)
            
            device.save()
            print(f"✅ Updated device: {device.name} ({device.ip_address})")
            updated_count += 1
            
        except Device.DoesNotExist:
            print(f"⚠️  Device not found: {ip_address}")
    
    print(f"\n📊 Summary: {updated_count} devices updated")
    return updated_count

def main():
    """Main function"""
    print("🔄 Updating Sample Data for Django Network Monitor")
    print("=" * 60)
    
    try:
        # Update existing devices
        device_count = update_existing_devices()
        
        print("\n🎉 Sample data update completed!")
        print(f"📱 You can now access the enhanced application:")
        print(f"   Web Interface: http://127.0.0.1:8000")
        print(f"   Device List:   http://127.0.0.1:8000/devices/")
        
        if device_count > 0:
            print(f"\n💡 New features available:")
            print(f"   ✅ Enhanced device filtering (IP, Host, Location, ISP)")
            print(f"   ✅ Real-time latency and speed data")
            print(f"   ✅ Traceroute functionality")
            print(f"   ✅ Advanced device actions")
            print(f"   ✅ Geolocation information")
        
    except Exception as e:
        print(f"❌ Error updating sample data: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
