#!/usr/bin/env python3
"""
Cleanup demo data and add geolocation to devices
"""
import os
import sys
import django
import requests
import time
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from django.db import models
from devices.models import Device
from monitoring.models import PingResult, SpeedTestResult, TracerouteResult
from alerts.models import Alert


def cleanup_demo_data():
    """Remove all demo/test data"""
    print("🧹 Cleaning up demo data...")
    
    # Delete test devices (keep user's real devices)
    demo_devices = Device.objects.filter(
        models.Q(name__icontains='test') |
        models.Q(name__icontains='demo') |
        models.Q(name__icontains='sample') |
        models.Q(ip_address__startswith='192.168.') |
        models.Q(ip_address__startswith='10.') |
        models.Q(ip_address__startswith='172.16.') |
        models.Q(ip_address__startswith='172.17.') |
        models.Q(ip_address__startswith='172.18.')
    ).exclude(
        # Keep devices that look like real infrastructure
        models.Q(name__icontains='router') |
        models.Q(name__icontains='switch') |
        models.Q(name__icontains='firewall') |
        models.Q(name__icontains='server')
    )
    
    demo_count = demo_devices.count()
    if demo_count > 0:
        demo_devices.delete()
        print(f"✅ Removed {demo_count} demo devices")
    
    # Clean up old monitoring results (keep last 7 days)
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=7)
    
    old_pings = PingResult.objects.filter(timestamp__lt=cutoff_date).count()
    if old_pings > 0:
        PingResult.objects.filter(timestamp__lt=cutoff_date).delete()
        print(f"✅ Removed {old_pings} old ping results")
    
    old_speeds = SpeedTestResult.objects.filter(timestamp__lt=cutoff_date).count()
    if old_speeds > 0:
        SpeedTestResult.objects.filter(timestamp__lt=cutoff_date).delete()
        print(f"✅ Removed {old_speeds} old speed test results")
    
    old_traces = TracerouteResult.objects.filter(timestamp__lt=cutoff_date).count()
    if old_traces > 0:
        TracerouteResult.objects.filter(timestamp__lt=cutoff_date).delete()
        print(f"✅ Removed {old_traces} old traceroute results")
    
    # Clean up resolved alerts
    old_alerts = Alert.objects.filter(is_active=False, created_at__lt=cutoff_date).count()
    if old_alerts > 0:
        Alert.objects.filter(is_active=False, created_at__lt=cutoff_date).delete()
        print(f"✅ Removed {old_alerts} old alerts")


def get_geolocation(ip_address):
    """Get geolocation for an IP address using free API"""
    try:
        # Using ip-api.com (free, no API key required)
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                return {
                    'latitude': Decimal(str(data.get('lat', 0))),
                    'longitude': Decimal(str(data.get('lon', 0))),
                    'city': data.get('city', ''),
                    'country': data.get('country', ''),
                    'isp': data.get('isp', ''),
                    'organization': data.get('org', ''),
                }
        
        # Fallback to ipinfo.io
        response = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                return {
                    'latitude': Decimal(lat),
                    'longitude': Decimal(lon),
                    'city': data.get('city', ''),
                    'country': data.get('country', ''),
                    'isp': data.get('org', ''),
                    'organization': data.get('org', ''),
                }
    
    except Exception as e:
        print(f"❌ Error getting geolocation for {ip_address}: {e}")
    
    return None


def add_geolocation_to_devices():
    """Add geolocation data to devices"""
    print("\n🌍 Adding geolocation data to devices...")
    
    devices_without_geo = Device.objects.filter(
        models.Q(latitude__isnull=True) | models.Q(longitude__isnull=True)
    ).exclude(
        # Skip private IP addresses
        models.Q(ip_address__startswith='192.168.') |
        models.Q(ip_address__startswith='10.') |
        models.Q(ip_address__startswith='172.16.') |
        models.Q(ip_address__startswith='172.17.') |
        models.Q(ip_address__startswith='172.18.') |
        models.Q(ip_address__startswith='172.19.') |
        models.Q(ip_address__startswith='172.20.') |
        models.Q(ip_address__startswith='172.21.') |
        models.Q(ip_address__startswith='172.22.') |
        models.Q(ip_address__startswith='172.23.') |
        models.Q(ip_address__startswith='172.24.') |
        models.Q(ip_address__startswith='172.25.') |
        models.Q(ip_address__startswith='172.26.') |
        models.Q(ip_address__startswith='172.27.') |
        models.Q(ip_address__startswith='172.28.') |
        models.Q(ip_address__startswith='172.29.') |
        models.Q(ip_address__startswith='172.30.') |
        models.Q(ip_address__startswith='172.31.') |
        models.Q(ip_address__startswith='127.') |
        models.Q(ip_address__startswith='169.254.')
    )
    
    total_devices = devices_without_geo.count()
    print(f"📍 Found {total_devices} devices needing geolocation")
    
    if total_devices == 0:
        print("✅ All devices already have geolocation data")
        return
    
    updated_count = 0
    
    for i, device in enumerate(devices_without_geo, 1):
        print(f"🔍 Processing {device.name} ({device.ip_address}) [{i}/{total_devices}]")
        
        geo_data = get_geolocation(device.ip_address)
        
        if geo_data:
            device.latitude = geo_data['latitude']
            device.longitude = geo_data['longitude']
            
            # Update location info if not already set
            if not device.city and geo_data['city']:
                device.city = geo_data['city']
            if not device.country and geo_data['country']:
                device.country = geo_data['country']
            if not device.isp and geo_data['isp']:
                device.isp = geo_data['isp']
            if not device.organization and geo_data['organization']:
                device.organization = geo_data['organization']
            
            device.save()
            updated_count += 1
            
            print(f"✅ Updated {device.name}: {geo_data['city']}, {geo_data['country']}")
        else:
            print(f"❌ Could not get geolocation for {device.name}")
        
        # Rate limiting - be nice to free APIs
        if i < total_devices:
            time.sleep(1)  # 1 second delay between requests
    
    print(f"\n🎉 Geolocation update completed!")
    print(f"✅ Updated {updated_count} devices")
    print(f"❌ Failed {total_devices - updated_count} devices")


def add_donation_info():
    """Add donation information to the database"""
    print("\n💝 Adding donation information...")
    
    # This could be stored in a settings model or configuration
    # For now, we'll just print the info
    print("✅ Donation information will be displayed in the UI")
    print("   - GitHub: https://github.com/vallururavi27/Multi-Network-Devices-Monitoring")
    print("   - PayPal: https://paypal.me/vallururavi27")


def main():
    """Main function"""
    print("🎯 Network Monitor - Cleanup and Geolocation Tool")
    print("=" * 60)
    
    try:
        # Ask user what to do
        print("Available actions:")
        print("1. Clean up demo data")
        print("2. Add geolocation to devices")
        print("3. Both (recommended)")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == '1':
            cleanup_demo_data()
        elif choice == '2':
            add_geolocation_to_devices()
        elif choice == '3':
            cleanup_demo_data()
            add_geolocation_to_devices()
            add_donation_info()
        elif choice == '4':
            print("👋 Goodbye!")
            return
        else:
            print("❌ Invalid choice")
            return
        
        print(f"\n🎉 Operation completed successfully!")
        print(f"🌐 Access your network monitor: http://127.0.0.1:8000/")
        print(f"🗺️  View device map: http://127.0.0.1:8000/devices/map/")
        
        # Show current device count
        total_devices = Device.objects.filter(is_active=True).count()
        devices_with_geo = Device.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        ).count()
        
        print(f"\n📊 Current Status:")
        print(f"   Total active devices: {total_devices}")
        print(f"   Devices with geolocation: {devices_with_geo}")
        print(f"   Devices ready for map: {devices_with_geo}")
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
