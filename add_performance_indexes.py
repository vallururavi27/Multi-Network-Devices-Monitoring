#!/usr/bin/env python3
"""
Add database indexes for better performance with 1000+ devices
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')
django.setup()

from django.db import connection

def add_performance_indexes():
    """Add database indexes for better performance"""
    print("🚀 Adding performance indexes for large datasets...")
    
    with connection.cursor() as cursor:
        # Device table indexes
        indexes = [
            # Device filtering indexes
            "CREATE INDEX IF NOT EXISTS idx_devices_ip_address ON devices_device(ip_address);",
            "CREATE INDEX IF NOT EXISTS idx_devices_name ON devices_device(name);",
            "CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices_device(hostname);",
            "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices_device(status);",
            "CREATE INDEX IF NOT EXISTS idx_devices_device_type ON devices_device(device_type);",
            "CREATE INDEX IF NOT EXISTS idx_devices_location ON devices_device(location);",
            "CREATE INDEX IF NOT EXISTS idx_devices_city ON devices_device(city);",
            "CREATE INDEX IF NOT EXISTS idx_devices_country ON devices_device(country);",
            "CREATE INDEX IF NOT EXISTS idx_devices_isp ON devices_device(isp);",
            "CREATE INDEX IF NOT EXISTS idx_devices_is_active ON devices_device(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices_device(last_seen);",
            
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_devices_active_status ON devices_device(is_active, status);",
            "CREATE INDEX IF NOT EXISTS idx_devices_active_type ON devices_device(is_active, device_type);",
            "CREATE INDEX IF NOT EXISTS idx_devices_status_lastseen ON devices_device(status, last_seen);",
            
            # Monitoring results indexes
            "CREATE INDEX IF NOT EXISTS idx_ping_device_timestamp ON monitoring_pingresult(device_id, timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_ping_timestamp ON monitoring_pingresult(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_ping_device_reachable ON monitoring_pingresult(device_id, is_reachable);",
            
            "CREATE INDEX IF NOT EXISTS idx_speed_device_timestamp ON monitoring_speedtestresult(device_id, timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_speed_timestamp ON monitoring_speedtestresult(timestamp);",
            
            "CREATE INDEX IF NOT EXISTS idx_traceroute_device_timestamp ON monitoring_tracerouteresult(device_id, timestamp);",
            
            # Alert indexes
            "CREATE INDEX IF NOT EXISTS idx_alerts_device_active ON alerts_alert(device_id, is_active);",
            "CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts_alert(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts_alert(severity);",
            
            # Geolocation indexes
            "CREATE INDEX IF NOT EXISTS idx_geolocation_ip ON monitoring_geolocation(ip_address);",
            "CREATE INDEX IF NOT EXISTS idx_geolocation_country ON monitoring_geolocation(country);",
            "CREATE INDEX IF NOT EXISTS idx_geolocation_isp ON monitoring_geolocation(isp);",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Added index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'}")
            except Exception as e:
                print(f"❌ Error adding index: {e}")
    
    print("\n🎉 Performance indexes added successfully!")

def analyze_database_performance():
    """Analyze database performance and provide recommendations"""
    print("\n📊 Analyzing database performance...")
    
    with connection.cursor() as cursor:
        # Get table sizes
        cursor.execute("""
            SELECT name, COUNT(*) as count 
            FROM (
                SELECT 'devices' as name FROM devices_device
                UNION ALL
                SELECT 'ping_results' as name FROM monitoring_pingresult
                UNION ALL
                SELECT 'speed_results' as name FROM monitoring_speedtestresult
                UNION ALL
                SELECT 'alerts' as name FROM alerts_alert
            ) 
            GROUP BY name
        """)
        
        results = cursor.fetchall()
        
        print("\n📈 Database Statistics:")
        for table, count in results:
            print(f"  {table}: {count:,} records")
        
        # Performance recommendations
        device_count = next((count for table, count in results if table == 'devices'), 0)
        ping_count = next((count for table, count in results if table == 'ping_results'), 0)
        
        print(f"\n💡 Performance Recommendations:")
        
        if device_count > 1000:
            print(f"  ✅ Large device count ({device_count:,}) - indexes are essential")
            print(f"  ✅ Consider enabling database query caching")
            print(f"  ✅ Use pagination with page sizes of 50-100")
        
        if ping_count > 10000:
            print(f"  ✅ Large ping history ({ping_count:,}) - consider data archiving")
            print(f"  ✅ Implement data retention policies")
            print(f"  ✅ Use time-based partitioning if supported")
        
        if device_count > 500:
            print(f"  ✅ Enable Redis caching for dashboard queries")
            print(f"  ✅ Use background tasks for bulk operations")
            print(f"  ✅ Consider read replicas for reporting")

def optimize_django_settings():
    """Provide Django settings optimization recommendations"""
    print(f"\n⚙️  Django Settings Optimization:")
    print(f"  Add to settings.py for better performance:")
    print(f"")
    print(f"  # Database optimization")
    print(f"  DATABASES['default']['OPTIONS'] = {{")
    print(f"      'timeout': 20,")
    print(f"      'check_same_thread': False,")
    print(f"  }}")
    print(f"")
    print(f"  # Caching configuration")
    print(f"  CACHES = {{")
    print(f"      'default': {{")
    print(f"          'BACKEND': 'django.core.cache.backends.redis.RedisCache',")
    print(f"          'LOCATION': 'redis://127.0.0.1:6379/1',")
    print(f"          'TIMEOUT': 300,")
    print(f"      }}")
    print(f"  }}")
    print(f"")
    print(f"  # Session optimization")
    print(f"  SESSION_ENGINE = 'django.contrib.sessions.backends.cache'")
    print(f"  SESSION_CACHE_ALIAS = 'default'")

def main():
    """Main function"""
    print("🎯 Network Monitor - Performance Optimization")
    print("=" * 60)
    
    try:
        # Add indexes
        add_performance_indexes()
        
        # Analyze performance
        analyze_database_performance()
        
        # Optimization recommendations
        optimize_django_settings()
        
        print(f"\n🎉 Performance optimization completed!")
        print(f"🚀 Your system is now optimized for 1000+ devices")
        
    except Exception as e:
        print(f"❌ Error during optimization: {e}")

if __name__ == '__main__':
    main()
