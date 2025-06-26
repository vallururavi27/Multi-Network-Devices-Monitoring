#!/usr/bin/env python3
"""
Generate 1000+ test devices for performance testing
"""
import os
import sys
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device, DeviceType, DeviceStatus

def generate_test_devices(count=1000):
    """Generate test devices for performance testing"""
    print(f"🚀 Generating {count} test devices for performance testing...")
    
    # Device name templates
    device_templates = [
        "Server-{:04d}",
        "Router-{:04d}",
        "Switch-{:04d}",
        "Workstation-{:04d}",
        "Printer-{:04d}",
        "Camera-{:04d}",
        "AP-{:04d}",
        "Phone-{:04d}",
    ]
    
    # Location templates
    locations = [
        "Building A - Floor 1", "Building A - Floor 2", "Building A - Floor 3",
        "Building B - Floor 1", "Building B - Floor 2", "Building B - Floor 3",
        "Data Center - Rack 1", "Data Center - Rack 2", "Data Center - Rack 3",
        "Network Closet A", "Network Closet B", "Network Closet C",
        "Office Area 1", "Office Area 2", "Office Area 3",
        "Conference Room A", "Conference Room B", "Conference Room C",
        "Warehouse", "Reception", "Security Office", "IT Room"
    ]
    
    # ISP templates
    isps = [
        "Comcast Business", "Verizon Business", "AT&T Business",
        "CenturyLink", "Charter Business", "Cox Business",
        "Local ISP", "Fiber Provider", "Cable Provider"
    ]
    
    # Cities
    cities = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
        "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte"
    ]
    
    device_types = [
        DeviceType.SERVER, DeviceType.ROUTER, DeviceType.SWITCH,
        DeviceType.WORKSTATION, DeviceType.PRINTER, DeviceType.OTHER
    ]
    
    statuses = [
        DeviceStatus.ONLINE, DeviceStatus.OFFLINE, 
        DeviceStatus.WARNING, DeviceStatus.UNKNOWN
    ]
    
    # Generate devices in batches for better performance
    batch_size = 100
    created_count = 0
    
    for batch_start in range(0, count, batch_size):
        batch_devices = []
        batch_end = min(batch_start + batch_size, count)
        
        for i in range(batch_start, batch_end):
            # Generate IP address
            # Use different subnets to simulate real network
            subnet = random.choice([
                "192.168.{}.{}",
                "10.{}.{}.{}",
                "172.16.{}.{}",
                "172.17.{}.{}",
                "172.18.{}.{}"
            ])
            
            if subnet.count('{}') == 2:
                ip_address = subnet.format(
                    random.randint(1, 254),
                    random.randint(1, 254)
                )
            else:
                ip_address = subnet.format(
                    random.randint(1, 254),
                    random.randint(1, 254),
                    random.randint(1, 254)
                )
            
            # Skip if IP already exists
            if Device.objects.filter(ip_address=ip_address).exists():
                continue
            
            # Generate device name
            template = random.choice(device_templates)
            device_name = template.format(i + 1)
            
            # Generate other attributes
            device_type = random.choice(device_types)
            status = random.choice(statuses)
            location = random.choice(locations)
            isp = random.choice(isps)
            city = random.choice(cities)
            
            # Generate performance metrics
            if status == DeviceStatus.ONLINE:
                latency = random.uniform(1.0, 50.0)
                download_speed = random.uniform(50.0, 1000.0)
                upload_speed = random.uniform(10.0, 100.0)
            elif status == DeviceStatus.WARNING:
                latency = random.uniform(100.0, 500.0)
                download_speed = random.uniform(10.0, 50.0)
                upload_speed = random.uniform(1.0, 10.0)
            else:
                latency = None
                download_speed = None
                upload_speed = None
            
            device = Device(
                name=device_name,
                ip_address=ip_address,
                hostname=f"{device_name.lower().replace('-', '')}.local",
                device_type=device_type,
                status=status,
                location=location,
                city=city,
                country="USA",
                isp=isp,
                organization="Test Organization",
                current_latency=latency,
                current_download_speed=download_speed,
                current_upload_speed=upload_speed,
                ping_enabled=True,
                alert_enabled=random.choice([True, False]),
                is_active=True,
            )
            
            batch_devices.append(device)
        
        # Bulk create for better performance
        try:
            Device.objects.bulk_create(batch_devices, ignore_conflicts=True)
            created_count += len(batch_devices)
            print(f"✅ Created batch {batch_start//batch_size + 1}: {len(batch_devices)} devices")
        except Exception as e:
            print(f"❌ Error creating batch {batch_start//batch_size + 1}: {e}")
    
    print(f"\n🎉 Successfully created {created_count} test devices!")
    return created_count

def generate_performance_test_data():
    """Generate additional test data for performance testing"""
    print("\n📊 Generating performance test data...")
    
    from monitoring.models import PingResult, SpeedTestResult
    from django.utils import timezone
    from datetime import timedelta
    
    devices = Device.objects.all()[:100]  # Use first 100 devices for test data
    
    # Generate ping results for last 7 days
    for device in devices:
        for day in range(7):
            date = timezone.now() - timedelta(days=day)
            
            # Generate 24 ping results per day (hourly)
            for hour in range(24):
                timestamp = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                is_reachable = random.choice([True] * 9 + [False])  # 90% success rate
                response_time = random.uniform(1.0, 100.0) if is_reachable else None
                
                PingResult.objects.create(
                    device=device,
                    is_reachable=is_reachable,
                    response_time=response_time,
                    packet_loss=0.0 if is_reachable else 100.0,
                    packets_sent=4,
                    packets_received=4 if is_reachable else 0,
                    timestamp=timestamp
                )
    
    print("✅ Generated ping test data")
    
    # Generate speed test results
    for device in devices[:20]:  # Speed tests for fewer devices
        for day in range(7):
            timestamp = timezone.now() - timedelta(days=day, hours=random.randint(0, 23))
            
            SpeedTestResult.objects.create(
                device=device,
                download_speed=random.uniform(50.0, 1000.0),
                upload_speed=random.uniform(10.0, 100.0),
                ping_latency=random.uniform(1.0, 50.0),
                jitter=random.uniform(1.0, 10.0),
                packet_loss_percent=random.uniform(0.0, 2.0),
                server_name=f"Test Server {random.randint(1, 5)}",
                server_location=random.choice(["New York", "Chicago", "Los Angeles"]),
                test_duration=random.uniform(30.0, 60.0),
                is_successful=True,
                timestamp=timestamp
            )
    
    print("✅ Generated speed test data")

def main():
    """Main function"""
    print("🎯 Network Monitor - Performance Test Data Generator")
    print("=" * 60)
    
    try:
        # Ask user for number of devices
        while True:
            try:
                count = input("Enter number of devices to generate (default 1000): ").strip()
                if not count:
                    count = 1000
                else:
                    count = int(count)
                
                if count < 1 or count > 10000:
                    print("Please enter a number between 1 and 10000")
                    continue
                break
            except ValueError:
                print("Please enter a valid number")
        
        # Generate devices
        created_count = generate_test_devices(count)
        
        # Ask if user wants test data
        generate_data = input("\nGenerate performance test data? (y/n): ").strip().lower()
        if generate_data in ['y', 'yes']:
            generate_performance_test_data()
        
        print(f"\n🎉 Performance test setup completed!")
        print(f"📊 Total devices in system: {Device.objects.count()}")
        print(f"🌐 Access the application: http://127.0.0.1:8000/devices/")
        print(f"⚡ Performance mode will automatically activate for 500+ devices")
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
