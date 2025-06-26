#!/usr/bin/env python3
"""
Django Network Monitor Startup Script
Starts all required services for the network monitoring application
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

class NetworkMonitorStarter:
    def __init__(self):
        self.processes = []
        self.running = True
    
    def check_requirements(self):
        """Check if all requirements are met"""
        print("🔍 Checking requirements...")
        
        # Check if manage.py exists
        if not Path('manage.py').exists():
            print("❌ manage.py not found. Please run from Django project root.")
            return False
        
        # Check if Redis is running
        try:
            result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Redis is not running. Please start Redis server:")
                print("   redis-server")
                return False
            print("✅ Redis is running")
        except FileNotFoundError:
            print("❌ Redis CLI not found. Please install Redis.")
            return False
        
        # Check if database is set up
        try:
            result = subprocess.run([
                sys.executable, 'manage.py', 'check', '--database', 'default'
            ], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Database not set up. Running migrations...")
                self.run_migrations()
        except Exception as e:
            print(f"❌ Database check failed: {e}")
            return False
        
        print("✅ All requirements met")
        return True
    
    def run_migrations(self):
        """Run Django migrations"""
        print("🔄 Running database migrations...")
        try:
            subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
            print("✅ Migrations completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Migration failed: {e}")
            sys.exit(1)
    
    def start_celery_worker(self):
        """Start Celery worker"""
        print("🔄 Starting Celery worker...")
        try:
            process = subprocess.Popen([
                sys.executable, '-m', 'celery', '-A', 'network_monitor', 
                'worker', '--loglevel=info'
            ])
            self.processes.append(('Celery Worker', process))
            print("✅ Celery worker started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Celery worker: {e}")
            return False
    
    def start_celery_beat(self):
        """Start Celery beat scheduler"""
        print("🔄 Starting Celery beat scheduler...")
        try:
            process = subprocess.Popen([
                sys.executable, '-m', 'celery', '-A', 'network_monitor', 
                'beat', '--loglevel=info'
            ])
            self.processes.append(('Celery Beat', process))
            print("✅ Celery beat scheduler started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Celery beat: {e}")
            return False
    
    def start_django_server(self):
        """Start Django development server"""
        print("🔄 Starting Django server...")
        try:
            process = subprocess.Popen([
                sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'
            ])
            self.processes.append(('Django Server', process))
            print("✅ Django server started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Django server: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n🛑 Shutting down services...")
        self.running = False
        self.stop_all_processes()
        sys.exit(0)
    
    def stop_all_processes(self):
        """Stop all running processes"""
        for name, process in self.processes:
            try:
                print(f"🔄 Stopping {name}...")
                process.terminate()
                process.wait(timeout=10)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
    
    def monitor_processes(self):
        """Monitor running processes"""
        while self.running:
            time.sleep(5)
            
            for i, (name, process) in enumerate(self.processes):
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    # Optionally restart the process
                    if name == "Django Server":
                        print("🔄 Restarting Django server...")
                        new_process = subprocess.Popen([
                            sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'
                        ])
                        self.processes[i] = (name, new_process)
    
    def create_sample_data(self):
        """Create sample devices for testing"""
        print("🔄 Creating sample data...")
        try:
            # Create sample devices using Django management command
            sample_script = """
from devices.models import Device, DeviceType, DeviceStatus

# Create sample devices if none exist
if Device.objects.count() == 0:
    devices = [
        {
            'name': 'Google DNS',
            'ip_address': '8.8.8.8',
            'description': 'Google Public DNS Server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
        },
        {
            'name': 'Cloudflare DNS',
            'ip_address': '1.1.1.1',
            'description': 'Cloudflare Public DNS Server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
        },
        {
            'name': 'Local Gateway',
            'ip_address': '192.168.1.1',
            'description': 'Default local network gateway',
            'device_type': DeviceType.ROUTER,
            'location': 'Local Network',
        },
        {
            'name': 'OpenDNS',
            'ip_address': '208.67.222.222',
            'description': 'OpenDNS Public Server',
            'device_type': DeviceType.DNS_SERVER,
            'location': 'Internet',
        }
    ]
    
    for device_data in devices:
        Device.objects.create(**device_data)
    
    print(f"Created {len(devices)} sample devices")
else:
    print("Sample devices already exist")
            """
            
            with open('create_samples.py', 'w') as f:
                f.write(sample_script)
            
            subprocess.run([
                sys.executable, 'manage.py', 'shell', '-c', 
                'exec(open("create_samples.py").read())'
            ], check=True)
            
            os.unlink('create_samples.py')
            print("✅ Sample data created")
            
        except Exception as e:
            print(f"⚠️  Could not create sample data: {e}")
    
    def start(self):
        """Start all services"""
        print("🚀 Django Network Monitor Startup")
        print("=" * 50)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check requirements
        if not self.check_requirements():
            sys.exit(1)
        
        # Create sample data
        self.create_sample_data()
        
        # Start services
        print("\n🔧 Starting services...")
        
        if not self.start_celery_worker():
            sys.exit(1)
        
        time.sleep(2)  # Give worker time to start
        
        if not self.start_celery_beat():
            sys.exit(1)
        
        time.sleep(2)  # Give beat time to start
        
        if not self.start_django_server():
            sys.exit(1)
        
        print("\n🎉 All services started successfully!")
        print("\n📱 Access the application:")
        print("   Web Interface: http://127.0.0.1:8000")
        print("   Admin Panel:   http://127.0.0.1:8000/admin/")
        print("   API Docs:      http://127.0.0.1:8000/api/")
        print("\n💡 Tips:")
        print("   - Create a superuser: python manage.py createsuperuser")
        print("   - View logs in the terminal windows")
        print("   - Press Ctrl+C to stop all services")
        print("\n🔄 Monitoring processes...")
        
        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)


def main():
    """Main function"""
    starter = NetworkMonitorStarter()
    starter.start()


if __name__ == '__main__':
    main()
