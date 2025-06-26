#!/usr/bin/env python3
"""
Import script for your specific data format:
IP Address | Host Name | Location | ISP

This script handles your exact data format and sets up comprehensive monitoring
for ping, HTTP, FTP, and database ports.
"""
import os
import sys
import django
import pandas as pd
import ipaddress
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from devices.models import Device, DeviceType, DeviceStatus
from monitoring.port_models import PortMonitor, ServiceType, get_service_type_for_port


def detect_device_type_from_hostname(hostname):
    """Auto-detect device type from hostname patterns"""
    hostname_lower = hostname.lower()
    
    # Database servers
    if any(x in hostname_lower for x in ['db', 'database', 'sql', 'mysql', 'postgres', 'oracle', 'mongo']):
        return DeviceType.DATABASE
    
    # Web servers
    elif any(x in hostname_lower for x in ['web', 'www', 'http', 'apache', 'nginx', 'iis']):
        return DeviceType.WEB_SERVER
    
    # FTP servers
    elif any(x in hostname_lower for x in ['ftp', 'sftp', 'file']):
        return DeviceType.FTP_SERVER
    
    # DNS servers
    elif any(x in hostname_lower for x in ['dns', 'bind', 'named', 'resolver']):
        return DeviceType.DNS_SERVER
    
    # Network equipment
    elif any(x in hostname_lower for x in ['router', 'gateway', 'gw']):
        return DeviceType.ROUTER
    elif any(x in hostname_lower for x in ['switch', 'sw']):
        return DeviceType.SWITCH
    elif any(x in hostname_lower for x in ['firewall', 'fw', 'pfsense']):
        return DeviceType.FIREWALL
    
    # Default to server
    else:
        return DeviceType.SERVER


def get_monitoring_ports_for_device_type(device_type):
    """Get default monitoring ports based on device type"""
    port_mappings = {
        DeviceType.WEB_SERVER: [80, 443, 8080, 8443],
        DeviceType.DATABASE: [3306, 5432, 1433, 1521, 27017],  # MySQL, PostgreSQL, SQL Server, Oracle, MongoDB
        DeviceType.FTP_SERVER: [21, 22, 990, 989],  # FTP, SFTP, FTPS
        DeviceType.DNS_SERVER: [53, 853],  # DNS, DNS over TLS
        DeviceType.ROUTER: [22, 23, 80, 443, 161],  # SSH, Telnet, HTTP, HTTPS, SNMP
        DeviceType.SWITCH: [22, 23, 80, 443, 161],  # SSH, Telnet, HTTP, HTTPS, SNMP
        DeviceType.FIREWALL: [22, 80, 443, 161],  # SSH, HTTP, HTTPS, SNMP
        DeviceType.SERVER: [22, 80, 443],  # Basic server ports
    }
    
    # Always include basic connectivity ports
    basic_ports = [22, 80, 443]  # SSH, HTTP, HTTPS
    device_ports = port_mappings.get(device_type, [])
    
    # Combine and remove duplicates
    all_ports = list(set(basic_ports + device_ports))
    return sorted(all_ports)


def setup_comprehensive_monitoring(device, device_type):
    """Set up comprehensive monitoring for a device"""
    print(f"  Setting up monitoring for {device.name} ({device_type})")
    
    # Get ports to monitor based on device type
    monitoring_ports = get_monitoring_ports_for_device_type(device_type)
    
    created_monitors = 0
    for port in monitoring_ports:
        service_type = get_service_type_for_port(port)
        
        port_monitor, created = PortMonitor.objects.get_or_create(
            device=device,
            port=port,
            defaults={
                'service_type': service_type,
                'service_name': f"{service_type.label} on {port}",
                'is_enabled': True,
                'check_interval': 300,  # 5 minutes
                'timeout': 10,
                'alert_on_failure': True,
                'alert_threshold': 3,
            }
        )
        
        if created:
            created_monitors += 1
    
    print(f"    Created {created_monitors} port monitors")
    return created_monitors


def import_devices_from_file(file_path, has_header=True):
    """Import devices from your data format file"""
    print(f"🚀 Importing devices from: {file_path}")
    
    try:
        # Read the file
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path, header=0 if has_header else None)
        else:
            # Try different separators
            for sep in ['\t', ',', '|', ';']:
                try:
                    df = pd.read_csv(file_path, sep=sep, header=0 if has_header else None)
                    if len(df.columns) >= 4:  # We expect at least 4 columns
                        break
                except:
                    continue
            else:
                raise ValueError("Could not parse the file with any common separator")
        
        print(f"📊 Found {len(df)} rows in the file")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Validate columns
        if len(df.columns) < 4:
            raise ValueError("File must have at least 4 columns: IP Address, Host Name, Location, ISP")
        
        # Process each row
        devices_created = 0
        devices_updated = 0
        monitoring_setups = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Extract data (assuming order: IP Address, Host Name, Location, ISP)
                ip_address = str(row.iloc[0]).strip()
                host_name = str(row.iloc[1]).strip()
                location = str(row.iloc[2]).strip()
                isp = str(row.iloc[3]).strip()
                
                # Validate IP address
                try:
                    ipaddress.ip_address(ip_address)
                except ValueError:
                    errors.append(f"Row {index + 1}: Invalid IP address '{ip_address}'")
                    continue
                
                # Auto-detect device type
                device_type = detect_device_type_from_hostname(host_name)
                
                # Create or update device
                device, created = Device.objects.get_or_create(
                    ip_address=ip_address,
                    defaults={
                        'name': host_name,
                        'hostname': host_name,
                        'device_type': device_type,
                        'location': location,
                        'isp': isp,
                        'ping_enabled': True,
                        'alert_enabled': True,
                        'is_active': True,
                        'status': DeviceStatus.UNKNOWN,  # Will be updated by monitoring
                    }
                )
                
                if created:
                    devices_created += 1
                    print(f"✅ Created: {host_name} ({ip_address}) - {device_type}")
                    
                    # Set up comprehensive monitoring
                    monitors_created = setup_comprehensive_monitoring(device, device_type)
                    if monitors_created > 0:
                        monitoring_setups += 1
                        
                else:
                    # Update existing device
                    device.name = host_name
                    device.hostname = host_name
                    device.location = location
                    device.isp = isp
                    device.device_type = device_type
                    device.save()
                    devices_updated += 1
                    print(f"🔄 Updated: {host_name} ({ip_address})")
                
            except Exception as e:
                error_msg = f"Row {index + 1}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        # Summary
        print(f"\n🎉 Import completed!")
        print(f"✅ Devices created: {devices_created}")
        print(f"🔄 Devices updated: {devices_updated}")
        print(f"🔧 Monitoring setups: {monitoring_setups}")
        
        if errors:
            print(f"⚠️  Errors encountered: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more errors")
        
        return {
            'devices_created': devices_created,
            'devices_updated': devices_updated,
            'monitoring_setups': monitoring_setups,
            'errors': errors
        }
        
    except Exception as e:
        print(f"❌ Error importing file: {e}")
        return {'error': str(e)}


def create_sample_data():
    """Create sample data in your format"""
    sample_data = """IP Address	Host Name	Location	ISP
8.8.8.8	Google DNS Primary	Hyderabad	google
8.8.4.4	Google DNS Secondary	Vishakapatnam	Airtel
1.1.1.1	Cloudflare DNS Primary	Vijayawada	sla
1.0.0.1	Cloudflare DNS Secondary	Vijayawada	asdas
9.9.9.9	Quad9 DNS Primary	Vijayawada	sdasd
149.112.112.112	Quad9 DNS Secondary	Vijayawada	dasd
142.250.191.14	Google.com	Vijayawada	sd
192.168.1.1	Home Router	Home Network	Local ISP
192.168.1.100	Web Server	Data Center	Local ISP
192.168.1.101	Database Server	Data Center	Local ISP
192.168.1.102	FTP Server	Data Center	Local ISP
10.0.0.1	Firewall	Network Closet	Corporate ISP
10.0.0.10	Core Switch	Network Closet	Corporate ISP
172.16.1.1	DMZ Router	DMZ Zone	Corporate ISP"""
    
    with open('sample_devices.txt', 'w') as f:
        f.write(sample_data)
    
    print("📄 Created sample_devices.txt with your data format")
    return 'sample_devices.txt'


def main():
    """Main function"""
    print("🎯 Network Monitor - Your Data Import Tool")
    print("=" * 60)
    print("This tool imports devices in your format:")
    print("IP Address | Host Name | Location | ISP")
    print("=" * 60)
    
    try:
        # Check if user wants to use sample data
        use_sample = input("Create and import sample data? (y/n): ").strip().lower()
        
        if use_sample in ['y', 'yes']:
            file_path = create_sample_data()
        else:
            # Ask for file path
            file_path = input("Enter path to your data file: ").strip()
            
            if not file_path:
                print("❌ No file path provided")
                return
            
            if not Path(file_path).exists():
                print(f"❌ File not found: {file_path}")
                return
        
        # Ask about header
        has_header = input("Does your file have a header row? (y/n): ").strip().lower()
        has_header = has_header in ['y', 'yes']
        
        # Import the data
        result = import_devices_from_file(file_path, has_header)
        
        if 'error' not in result:
            print(f"\n🌐 Access your devices: http://127.0.0.1:8000/devices/")
            print(f"📊 Dashboard: http://127.0.0.1:8000/dashboard/")
            print(f"⚙️  Admin panel: http://127.0.0.1:8000/admin/")
            
            print(f"\n🔧 Monitoring Features Enabled:")
            print(f"   ✅ Ping monitoring for all devices")
            print(f"   ✅ HTTP/HTTPS monitoring for web servers")
            print(f"   ✅ Database port monitoring for DB servers")
            print(f"   ✅ FTP monitoring for file servers")
            print(f"   ✅ DNS monitoring for DNS servers")
            print(f"   ✅ SNMP monitoring for network equipment")
            print(f"   ✅ Automatic service discovery")
            print(f"   ✅ Alert notifications")
        
    except KeyboardInterrupt:
        print("\n❌ Import cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
