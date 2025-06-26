"""
Views for device management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import models

from .models import Device, DeviceGroup
from .forms import DeviceForm, DeviceGroupForm


def device_list(request):
    """List all devices with advanced filtering - optimized for 1000+ devices"""
    from django.core.cache import cache
    from django.db.models import Prefetch

    # Start with optimized queryset
    devices = Device.objects.select_related().only(
        'id', 'name', 'ip_address', 'hostname', 'device_type', 'location',
        'city', 'country', 'isp', 'organization', 'status', 'last_seen',
        'current_latency', 'current_upload_speed', 'current_download_speed',
        'is_active', 'ping_enabled'
    )

    # Apply filters with database indexes
    ip_filter = request.GET.get('ip_filter')
    if ip_filter:
        devices = devices.filter(ip_address__icontains=ip_filter)

    host_filter = request.GET.get('host_filter')
    if host_filter:
        devices = devices.filter(
            models.Q(name__icontains=host_filter) |
            models.Q(hostname__icontains=host_filter)
        )

    location_filter = request.GET.get('location_filter')
    if location_filter:
        devices = devices.filter(
            models.Q(location__icontains=location_filter) |
            models.Q(city__icontains=location_filter) |
            models.Q(country__icontains=location_filter)
        )

    isp_filter = request.GET.get('isp_filter')
    if isp_filter:
        devices = devices.filter(
            models.Q(isp__icontains=isp_filter) |
            models.Q(organization__icontains=isp_filter)
        )

    status_filter = request.GET.get('status_filter')
    if status_filter:
        devices = devices.filter(status=status_filter)

    type_filter = request.GET.get('type_filter')
    if type_filter:
        devices = devices.filter(device_type=type_filter)

    monitoring_filter = request.GET.get('monitoring_filter')
    if monitoring_filter == 'enabled':
        devices = devices.filter(is_active=True)
    elif monitoring_filter == 'disabled':
        devices = devices.filter(is_active=False)

    # Sorting with database indexes
    sort_by = request.GET.get('sort_by', 'name')
    order = request.GET.get('order', 'asc')

    valid_sort_fields = ['name', 'ip_address', 'status', 'last_seen', 'current_latency']
    if sort_by in valid_sort_fields:
        if order == 'desc':
            sort_by = f'-{sort_by}'
        devices = devices.order_by(sort_by)
    else:
        devices = devices.order_by('name')

    # Pagination optimized for large datasets
    page_size = int(request.GET.get('page_size', 50))  # Increased default page size
    page_size = min(page_size, 200)  # Cap at 200 for performance

    paginator = Paginator(devices, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add performance metrics for monitoring
    total_devices = devices.count() if not hasattr(devices, '_result_cache') else len(devices)

    context = {
        'page_obj': page_obj,
        'total_devices': total_devices,
        'page_size': page_size,
        'performance_mode': total_devices > 500,  # Enable performance mode for large datasets
    }
    return render(request, 'devices/list.html', context)


def device_detail(request, pk):
    """Device detail view"""
    device = get_object_or_404(Device, pk=pk)
    
    # Get recent ping results
    recent_pings = device.ping_results.order_by('-timestamp')[:20]
    
    # Get recent speed test results
    recent_speeds = device.speed_results.order_by('-timestamp')[:10]
    
    context = {
        'device': device,
        'recent_pings': recent_pings,
        'recent_speeds': recent_speeds,
        'uptime_24h': device.get_uptime_percentage(1),
        'avg_response_time': device.get_average_response_time(1),
    }
    return render(request, 'devices/detail.html', context)


def device_add(request):
    """Add new device"""
    if request.method == 'POST':
        # Handle form data manually for better control
        data = {
            'name': request.POST.get('name'),
            'ip_address': request.POST.get('ip_address'),
            'hostname': request.POST.get('hostname'),
            'description': request.POST.get('description'),
            'device_type': request.POST.get('device_type', 'server'),
            'location': request.POST.get('location'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country'),
            'isp': request.POST.get('isp'),
            'organization': request.POST.get('organization'),
            'ping_enabled': request.POST.get('ping_enabled') == 'on',
            'speed_test_enabled': request.POST.get('speed_test_enabled') == 'on',
            'alert_enabled': request.POST.get('alert_enabled') == 'on',
        }

        try:
            device = Device.objects.create(**data)
            messages.success(request, f'Device "{device.name}" has been added successfully.')
            return redirect('devices:detail', pk=device.pk)
        except Exception as e:
            messages.error(request, f'Error adding device: {str(e)}')

    context = {}
    return render(request, 'devices/add.html', context)


def device_edit(request, pk):
    """Edit device"""
    device = get_object_or_404(Device, pk=pk)

    if request.method == 'POST':
        # Handle form data manually for better control
        data = {
            'name': request.POST.get('name'),
            'ip_address': request.POST.get('ip_address'),
            'hostname': request.POST.get('hostname'),
            'description': request.POST.get('description'),
            'device_type': request.POST.get('device_type'),
            'location': request.POST.get('location'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country'),
            'isp': request.POST.get('isp'),
            'organization': request.POST.get('organization'),
            'ping_enabled': request.POST.get('ping_enabled') == 'on',
            'speed_test_enabled': request.POST.get('speed_test_enabled') == 'on',
            'alert_enabled': request.POST.get('alert_enabled') == 'on',
        }

        try:
            for field, value in data.items():
                setattr(device, field, value)
            device.save()
            messages.success(request, f'Device "{device.name}" has been updated successfully.')
            return redirect('devices:detail', pk=device.pk)
        except Exception as e:
            messages.error(request, f'Error updating device: {str(e)}')

    # Get device statistics
    uptime_24h = device.get_uptime_percentage(1)
    avg_response_time = device.get_average_response_time(1)

    context = {
        'device': device,
        'uptime_24h': uptime_24h,
        'avg_response_time': avg_response_time,
    }
    return render(request, 'devices/edit.html', context)


def device_delete(request, pk):
    """Delete device"""
    device = get_object_or_404(Device, pk=pk)
    
    if request.method == 'POST':
        device_name = device.name
        device.delete()
        messages.success(request, f'Device "{device_name}" has been deleted.')
        return redirect('devices:list')
    
    context = {'device': device}
    return render(request, 'devices/delete.html', context)


def device_import(request):
    """Import devices from Excel/CSV with support for 1000+ devices"""
    if request.method == 'POST':
        try:
            # Handle file upload
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                messages.error(request, 'Please select a file to upload.')
                return render(request, 'devices/import.html')

            # Get import settings
            has_header = request.POST.get('has_header') == 'on'
            update_existing = request.POST.get('update_existing') == 'on'
            ip_column = int(request.POST.get('ip_column', 0))
            name_column = request.POST.get('name_column')
            location_column = request.POST.get('location_column')
            isp_column = request.POST.get('isp_column')
            default_device_type = request.POST.get('default_device_type', 'server')
            auto_detect_type = request.POST.get('auto_detect_type') == 'on'

            # Monitoring settings
            enable_ping = request.POST.get('enable_ping') == 'on'
            enable_alerts = request.POST.get('enable_alerts') == 'on'
            enable_http = request.POST.get('enable_http') == 'on'
            enable_ftp = request.POST.get('enable_ftp') == 'on'
            enable_database = request.POST.get('enable_database') == 'on'
            enable_custom_ports = request.POST.get('enable_custom_ports') == 'on'
            custom_ports = request.POST.get('custom_ports', '')
            enable_snmp = request.POST.get('enable_snmp') == 'on'
            enable_speed_test = request.POST.get('enable_speed_test') == 'on'
            enable_ssl_check = request.POST.get('enable_ssl_check') == 'on'
            enable_dns_check = request.POST.get('enable_dns_check') == 'on'

            batch_size = int(request.POST.get('batch_size', 100))
            processing_mode = request.POST.get('processing_mode', 'async')

            # Process the file
            import pandas as pd
            import io

            # Read file based on type
            file_extension = uploaded_file.name.lower().split('.')[-1]

            if file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(uploaded_file, header=0 if has_header else None)
            elif file_extension == 'csv':
                df = pd.read_csv(uploaded_file, header=0 if has_header else None)
            else:
                # Handle text files
                content = uploaded_file.read().decode('utf-8')
                lines = content.strip().split('\n')
                if has_header:
                    lines = lines[1:]  # Skip header

                # Create DataFrame from text lines
                data = []
                for line in lines:
                    parts = line.split(',') if ',' in line else line.split()
                    if len(parts) > ip_column:
                        data.append(parts)

                df = pd.DataFrame(data)

            # Validate and process data
            devices_created = 0
            devices_updated = 0
            errors = []

            # Process in batches for better performance
            total_rows = len(df)

            for batch_start in range(0, total_rows, batch_size):
                batch_end = min(batch_start + batch_size, total_rows)
                batch_df = df.iloc[batch_start:batch_end]

                for index, row in batch_df.iterrows():
                    try:
                        # Extract IP address
                        ip_address = str(row.iloc[ip_column]).strip()

                        # Validate IP address
                        import ipaddress
                        try:
                            ipaddress.ip_address(ip_address)
                        except ValueError:
                            errors.append(f"Row {index + 1}: Invalid IP address '{ip_address}'")
                            continue

                        # Extract other fields
                        device_name = ip_address  # Default name
                        if name_column and name_column.isdigit():
                            name_col = int(name_column)
                            if len(row) > name_col:
                                device_name = str(row.iloc[name_col]).strip()

                        location = ""
                        if location_column and location_column.isdigit():
                            loc_col = int(location_column)
                            if len(row) > loc_col:
                                location = str(row.iloc[loc_col]).strip()

                        isp = ""
                        if isp_column and isp_column.isdigit():
                            isp_col = int(isp_column)
                            if len(row) > isp_col:
                                isp = str(row.iloc[isp_col]).strip()

                        # Auto-detect device type from hostname/IP patterns
                        detected_device_type = default_device_type
                        if auto_detect_type and device_name:
                            name_lower = device_name.lower()
                            if any(x in name_lower for x in ['db', 'database', 'sql', 'mysql', 'postgres', 'oracle']):
                                detected_device_type = 'database'
                            elif any(x in name_lower for x in ['web', 'www', 'http', 'apache', 'nginx']):
                                detected_device_type = 'web_server'
                            elif any(x in name_lower for x in ['ftp', 'sftp', 'file']):
                                detected_device_type = 'ftp_server'
                            elif any(x in name_lower for x in ['dns', 'bind', 'named']):
                                detected_device_type = 'dns_server'
                            elif any(x in name_lower for x in ['router', 'gateway', 'gw']):
                                detected_device_type = 'router'
                            elif any(x in name_lower for x in ['switch', 'sw']):
                                detected_device_type = 'switch'
                            elif any(x in name_lower for x in ['firewall', 'fw', 'pfsense']):
                                detected_device_type = 'firewall'

                        # Determine monitoring ports based on device type and settings
                        monitoring_ports = []
                        if enable_http:
                            monitoring_ports.extend([80, 443, 8080, 8443])
                        if enable_ftp:
                            monitoring_ports.extend([21, 22])
                        if enable_database:
                            monitoring_ports.extend([3306, 5432, 1433, 1521, 27017])
                        if enable_custom_ports and custom_ports:
                            try:
                                custom_port_list = [int(p.strip()) for p in custom_ports.split(',') if p.strip().isdigit()]
                                monitoring_ports.extend(custom_port_list)
                            except:
                                pass

                        # Check if device exists
                        device, created = Device.objects.get_or_create(
                            ip_address=ip_address,
                            defaults={
                                'name': device_name,
                                'device_type': detected_device_type,
                                'location': location,
                                'isp': isp,
                                'ping_enabled': enable_ping,
                                'alert_enabled': enable_alerts,
                                'is_active': True,
                            }
                        )

                        if created:
                            devices_created += 1

                            # Set up port monitoring for new devices
                            setup_device_monitoring(device, monitoring_ports, {
                                'enable_snmp': enable_snmp,
                                'enable_speed_test': enable_speed_test,
                                'enable_ssl_check': enable_ssl_check,
                                'enable_dns_check': enable_dns_check,
                            })

                        elif update_existing:
                            device.name = device_name
                            device.location = location
                            device.device_type = detected_device_type
                            device.isp = isp
                            device.ping_enabled = enable_ping
                            device.alert_enabled = enable_alerts
                            device.save()
                            devices_updated += 1

                    except Exception as e:
                        errors.append(f"Row {index + 1}: {str(e)}")

            # Show results
            if devices_created > 0:
                messages.success(request, f'Successfully imported {devices_created} new devices.')
            if devices_updated > 0:
                messages.success(request, f'Successfully updated {devices_updated} existing devices.')
            if errors:
                error_msg = f'{len(errors)} errors occurred during import. First few: ' + '; '.join(errors[:5])
                messages.warning(request, error_msg)

            return redirect('devices:list')

        except Exception as e:
            messages.error(request, f'Import failed: {str(e)}')

    context = {}
    return render(request, 'devices/import.html', context)


def setup_device_monitoring(device, monitoring_ports, monitoring_options):
    """Set up comprehensive monitoring for a device"""
    from monitoring.port_models import PortMonitor, get_service_type_for_port

    # Set up port monitoring
    for port in monitoring_ports:
        service_type = get_service_type_for_port(port)

        PortMonitor.objects.get_or_create(
            device=device,
            port=port,
            defaults={
                'service_type': service_type,
                'is_enabled': True,
                'check_interval': 300,  # 5 minutes
                'timeout': 10,
                'alert_on_failure': True,
                'alert_threshold': 3,
            }
        )

    # Schedule service discovery for comprehensive monitoring
    if monitoring_options.get('enable_snmp'):
        # Set up SNMP monitoring if enabled
        PortMonitor.objects.get_or_create(
            device=device,
            port=161,
            defaults={
                'service_type': 'snmp',
                'service_name': 'SNMP',
                'is_enabled': True,
                'check_interval': 600,  # 10 minutes
                'timeout': 15,
            }
        )

    # Auto-discover additional services
    try:
        from monitoring.service_tasks import auto_discover_services
        auto_discover_services.delay(device.id)
    except ImportError:
        # Fallback if Celery is not available
        pass


def device_export(request):
    """Export devices to Excel"""
    # TODO: Implement Excel export
    messages.info(request, 'Excel export feature coming soon!')
    return redirect('devices:list')


def group_list(request):
    """List device groups"""
    groups = DeviceGroup.objects.all().order_by('name')
    context = {'groups': groups}
    return render(request, 'devices/groups.html', context)


def group_add(request):
    """Add new device group"""
    if request.method == 'POST':
        form = DeviceGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Group "{group.name}" has been created.')
            return redirect('devices:group_detail', pk=group.pk)
    else:
        form = DeviceGroupForm()
    
    context = {'form': form}
    return render(request, 'devices/group_add.html', context)


def group_detail(request, pk):
    """Device group detail"""
    group = get_object_or_404(DeviceGroup, pk=pk)
    context = {'group': group}
    return render(request, 'devices/group_detail.html', context)
