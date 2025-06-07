#!/usr/bin/env python3
"""
Startup script for Gmail API Microservices
Runs all services: auth, gmail, email, user, and gateway
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.base_dir = Path(__file__).parent
        
        # Service configurations: (name, directory, port)
        self.services = [
            ("auth-service", "services/auth-service", 8001),
            ("gmail-service", "services/gmail-service", 5001),
            ("email-service", "services/email-service", 5002),
            ("user-service", "services/user-service", 5003),
            ("gateway", "gateway", 8080),
        ]
    
    def check_requirements(self):
        """Check if virtual environment is activated and required files exist"""
        # Check if virtual environment is activated
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("❌ Virtual environment not detected. Please activate your venv first:")
            print("   source venv/bin/activate  # or activate.bat on Windows")
            return False
        
        # Check if service directories exist
        for name, directory, port in self.services:
            service_path = self.base_dir / directory
            app_file = service_path / "src" / "app.py"
            
            if not service_path.exists():
                print(f"❌ Service directory not found: {directory}")
                return False
            
            if not app_file.exists():
                print(f"❌ App file not found: {app_file}")
                return False
        
        print("✅ All requirements check passed")
        return True
    
    def start_service(self, name, directory, port):
        """Start a single service"""
        service_path = self.base_dir / directory
        
        print(f"🚀 Starting {name} on port {port}...")
        
        try:
            # Change to service directory and run uvicorn
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "src.app:app", 
                "--host", "0.0.0.0", 
                "--port", str(port)
            ], 
            cwd=service_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None  # For proper process group handling
            )
            
            self.processes.append((name, process, port))
            print(f"✅ {name} started (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return False
    
    def start_all_services(self):
        """Start all services in order"""
        print("🌟 Starting Gmail API Microservices...")
        print("=" * 50)
        
        if not self.check_requirements():
            return False
        
        success_count = 0
        
        for name, directory, port in self.services:
            if self.start_service(name, directory, port):
                success_count += 1
                # Small delay between service starts
                time.sleep(1)
            else:
                print(f"❌ Failed to start {name}, stopping...")
                self.stop_all_services()
                return False
        
        print("=" * 50)
        print(f"🎉 All {success_count} services started successfully!")
        print("\n📋 Service Status:")
        
        for name, process, port in self.processes:
            print(f"   • {name:<15} → http://localhost:{port} (PID: {process.pid})")
        
        print(f"\n🌐 Main Gateway: http://localhost:8080")
        print(f"📚 API Docs: http://localhost:8080/docs")
        print("\n💡 Press Ctrl+C to stop all services")
        
        return True
    
    def stop_all_services(self):
        """Stop all running services"""
        print("\n🛑 Stopping all services...")
        
        for name, process, port in self.processes:
            try:
                print(f"   Stopping {name}...")
                
                if os.name == 'nt':  # Windows
                    process.terminate()
                else:  # Unix/Linux/Mac
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                # Wait for process to terminate
                process.wait(timeout=5)
                print(f"   ✅ {name} stopped")
                
            except subprocess.TimeoutExpired:
                print(f"   ⚠️ {name} didn't stop gracefully, forcing...")
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            
            except Exception as e:
                print(f"   ❌ Error stopping {name}: {e}")
        
        self.processes.clear()
        print("🏁 All services stopped")
    
    def monitor_services(self):
        """Monitor running services and handle shutdown"""
        try:
            while True:
                # Check if any service has died
                for i, (name, process, port) in enumerate(self.processes):
                    if process.poll() is not None:  # Process has terminated
                        print(f"\n❌ {name} has stopped unexpectedly!")
                        
                        # Get the error output
                        try:
                            stdout, stderr = process.communicate(timeout=1)
                            if stderr:
                                print(f"   Error: {stderr.decode()}")
                        except:
                            pass
                        
                        print("🛑 Stopping all services due to failure...")
                        self.stop_all_services()
                        return False
                
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print("\n👋 Received shutdown signal...")
            self.stop_all_services()
            return True

def main():
    """Main function"""
    manager = ServiceManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start all services
    if manager.start_all_services():
        # Monitor services until shutdown
        manager.monitor_services()
    
    print("👋 Gmail API Microservices shutdown complete")

if __name__ == "__main__":
    main()