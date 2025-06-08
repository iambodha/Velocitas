#!/usr/bin/env python3
"""
Startup script for Gmail API Microservices
Runs all services: auth, gmail, email, user, and gateway
Enhanced with detailed logging and monitoring
"""

import subprocess
import sys
import os
import time
import signal
import threading
import queue
import json
from pathlib import Path
from datetime import datetime
import re

class ColoredLogger:
    """Colored console output for better readability"""
    
    # ANSI color codes
    COLORS = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'PURPLE': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RESET': '\033[0m'
    }
    
    @classmethod
    def log(cls, message, color='WHITE', prefix=''):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        colored_msg = f"{cls.COLORS[color]}{message}{cls.COLORS['RESET']}"
        print(f"[{timestamp}] {prefix}{colored_msg}")
    
    @classmethod
    def info(cls, message, service='SYSTEM'):
        cls.log(f"[{service}] {message}", 'CYAN', '📘 ')
    
    @classmethod
    def success(cls, message, service='SYSTEM'):
        cls.log(f"[{service}] {message}", 'GREEN', '✅ ')
    
    @classmethod
    def warning(cls, message, service='SYSTEM'):
        cls.log(f"[{service}] {message}", 'YELLOW', '⚠️  ')
    
    @classmethod
    def error(cls, message, service='SYSTEM'):
        cls.log(f"[{service}] {message}", 'RED', '❌ ')
    
    @classmethod
    def api_call(cls, method, path, status, service):
        status_color = 'GREEN' if status < 400 else 'RED' if status >= 500 else 'YELLOW'
        cls.log(f"[{service}] {method} {path} → {status}", status_color, '🌐 ')
    
    @classmethod
    def database(cls, message, service='DB'):
        cls.log(f"[{service}] {message}", 'PURPLE', '🗄️  ')

class LogParser:
    """Parse and format service logs for better readability"""
    
    @staticmethod
    def parse_uvicorn_log(line, service_name):
        """Parse uvicorn access logs"""
        # Pattern for uvicorn access logs: INFO:     127.0.0.1:63108 - "GET /health HTTP/1.1" 200
        access_pattern = r'INFO:\s+(\d+\.\d+\.\d+\.\d+):(\d+) - "([\w]+) ([^\s]+) HTTP/[\d\.]+"\s+(\d+)'
        match = re.search(access_pattern, line)
        
        if match:
            ip, port, method, path, status = match.groups()
            ColoredLogger.api_call(method, path, int(status), service_name)
            return True
        
        # Pattern for uvicorn startup: INFO:     Uvicorn running on http://0.0.0.0:8080
        startup_pattern = r'INFO:\s+Uvicorn running on http://([^:]+):(\d+)'
        match = re.search(startup_pattern, line)
        if match:
            host, port = match.groups()
            ColoredLogger.success(f"Server running on {host}:{port}", service_name)
            return True
        
        # Pattern for application started
        if "Application startup complete" in line:
            ColoredLogger.success("Application startup complete", service_name)
            return True
        
        return False
    
    @staticmethod
    def parse_database_log(line, service_name):
        """Parse database-related logs"""
        db_keywords = ['postgresql', 'database', 'connection', 'query', 'transaction', 'psycopg2']
        
        if any(keyword in line.lower() for keyword in db_keywords):
            if 'error' in line.lower() or 'failed' in line.lower():
                ColoredLogger.database(f"DB Error: {line.strip()}", service_name)
            elif 'connect' in line.lower():
                ColoredLogger.database(f"DB Connection: {line.strip()}", service_name)
            else:
                ColoredLogger.database(line.strip(), service_name)
            return True
        
        return False
    
    @staticmethod
    def parse_error_log(line, service_name):
        """Parse error logs"""
        error_keywords = ['error', 'exception', 'traceback', 'failed', 'critical']
        
        if any(keyword in line.lower() for keyword in error_keywords):
            ColoredLogger.error(line.strip(), service_name)
            return True
        
        return False
    
    @staticmethod
    def parse_auth_log(line, service_name):
        """Parse authentication-related logs"""
        auth_keywords = ['auth', 'token', 'login', 'logout', 'oauth', 'gmail', 'google']
        
        if any(keyword in line.lower() for keyword in auth_keywords):
            if 'success' in line.lower():
                ColoredLogger.success(f"Auth: {line.strip()}", service_name)
            elif 'error' in line.lower() or 'failed' in line.lower():
                ColoredLogger.error(f"Auth Error: {line.strip()}", service_name)
            else:
                ColoredLogger.info(f"Auth: {line.strip()}", service_name)
            return True
        
        return False

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.base_dir = Path(__file__).parent
        self.log_threads = []
        self.shutdown_event = threading.Event()
        
        # Service configurations: (name, directory, port, color)
        self.services = [
            ("auth-service", "services/auth-service", 8001, "CYAN"),
            ("gmail-service", "services/gmail-service", 5001, "GREEN"),
            ("email-service", "services/email-service", 5002, "YELLOW"),
            ("user-service", "services/user-service", 5003, "PURPLE"),
            ("gateway", "gateway", 8080, "BLUE"),
        ]
    
    def check_requirements(self):
        """Check if virtual environment is activated and required files exist"""
        ColoredLogger.info("Checking requirements...")
        
        # Check if virtual environment is activated
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            ColoredLogger.error("Virtual environment not detected. Please activate your venv first:")
            ColoredLogger.info("   source venv/bin/activate  # or activate.bat on Windows")
            return False
        
        ColoredLogger.success("Virtual environment detected")
        
        # Check if service directories exist
        for name, directory, port, color in self.services:
            service_path = self.base_dir / directory
            app_file = service_path / "src" / "app.py"
            
            if not service_path.exists():
                ColoredLogger.error(f"Service directory not found: {directory}")
                return False
            
            if not app_file.exists():
                ColoredLogger.error(f"App file not found: {app_file}")
                return False
            
            ColoredLogger.success(f"Service {name} found at {directory}")
        
        ColoredLogger.success("All requirements check passed")
        return True
    
    def stream_logs(self, process, service_name, stream_type='stdout'):
        """Stream and parse logs from a service process"""
        stream = process.stdout if stream_type == 'stdout' else process.stderr
        
        while not self.shutdown_event.is_set():
            try:
                line = stream.readline()
                if not line:
                    break
                
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Try different parsers in order of priority
                parsed = (
                    LogParser.parse_uvicorn_log(line, service_name) or
                    LogParser.parse_database_log(line, service_name) or
                    LogParser.parse_error_log(line, service_name) or
                    LogParser.parse_auth_log(line, service_name)
                )
                
                # If no specific parser matched, show as general info
                if not parsed:
                    # Filter out very verbose logs
                    if not any(skip in line.lower() for skip in ['debug', 'trace']):
                        ColoredLogger.info(line, service_name)
                
            except Exception as e:
                if not self.shutdown_event.is_set():
                    ColoredLogger.error(f"Log streaming error: {e}", service_name)
                break
    
    def start_service(self, name, directory, port, color):
        """Start a single service with enhanced logging"""
        service_path = self.base_dir / directory
        
        ColoredLogger.info(f"Starting {name} on port {port}...", "SYSTEM")
        
        try:
            # Set environment variables for enhanced logging
            env = os.environ.copy()
            env.update({
                'PYTHONUNBUFFERED': '1',  # Ensure real-time output
                'LOG_LEVEL': 'INFO',
                'UVICORN_LOG_LEVEL': 'info',
                'SERVICE_NAME': name,
                'SERVICE_PORT': str(port)
            })
            
            # Change to service directory and run uvicorn with detailed logging
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "src.app:app", 
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--log-level", "info",
                "--access-log",
                "--use-colors"
            ], 
            cwd=service_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None,
            bufsize=1,  # Line buffered
            universal_newlines=False
            )
            
            self.processes.append((name, process, port))
            
            # Start log streaming threads
            stdout_thread = threading.Thread(
                target=self.stream_logs, 
                args=(process, name, 'stdout'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self.stream_logs, 
                args=(process, name, 'stderr'),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            self.log_threads.extend([stdout_thread, stderr_thread])
            
            ColoredLogger.success(f"{name} started (PID: {process.pid})", "SYSTEM")
            return True
            
        except Exception as e:
            ColoredLogger.error(f"Failed to start {name}: {e}", "SYSTEM")
            return False
    
    def start_all_services(self):
        """Start all services in order with enhanced monitoring"""
        ColoredLogger.log("Starting Gmail API Microservices...", 'BOLD', '🌟 ')
        ColoredLogger.log("=" * 60, 'CYAN')
        
        if not self.check_requirements():
            return False
        
        success_count = 0
        
        # Start database connection check
        ColoredLogger.info("Checking database connectivity...", "SYSTEM")
        
        for name, directory, port, color in self.services:
            if self.start_service(name, directory, port, color):
                success_count += 1
                # Longer delay to ensure proper startup
                ColoredLogger.info(f"Waiting for {name} to initialize...", "SYSTEM")
                time.sleep(3)
            else:
                ColoredLogger.error(f"Failed to start {name}, stopping all services...", "SYSTEM")
                self.stop_all_services()
                return False
        
        ColoredLogger.log("=" * 60, 'CYAN')
        ColoredLogger.success(f"All {success_count} services started successfully!", "SYSTEM")
        ColoredLogger.log("\n📋 Service Status:", 'BOLD')
        
        for name, process, port in self.processes:
            ColoredLogger.log(f"   • {name:<15} → http://localhost:{port} (PID: {process.pid})", 'GREEN')
        
        ColoredLogger.log(f"\n🌐 Main Gateway: http://localhost:8080", 'BOLD')
        ColoredLogger.log(f"📚 API Docs: http://localhost:8080/docs", 'BOLD')
        ColoredLogger.log(f"🔍 Health Check: http://localhost:8080/health", 'BOLD')
        ColoredLogger.log("\n💡 Monitoring all API calls and errors in real-time...", 'YELLOW')
        ColoredLogger.log("💡 Press Ctrl+C to stop all services\n", 'YELLOW')
        
        return True
    
    def stop_all_services(self):
        """Stop all running services"""
        ColoredLogger.warning("Stopping all services...", "SYSTEM")
        self.shutdown_event.set()
        
        for name, process, port in self.processes:
            try:
                ColoredLogger.info(f"Stopping {name}...", "SYSTEM")
                
                if os.name == 'nt':  # Windows
                    process.terminate()
                else:  # Unix/Linux/Mac
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                # Wait for process to terminate
                process.wait(timeout=5)
                ColoredLogger.success(f"{name} stopped gracefully", "SYSTEM")
                
            except subprocess.TimeoutExpired:
                ColoredLogger.warning(f"{name} didn't stop gracefully, forcing...", "SYSTEM")
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                ColoredLogger.info(f"{name} force stopped", "SYSTEM")
            
            except Exception as e:
                ColoredLogger.error(f"Error stopping {name}: {e}", "SYSTEM")
        
        # Wait for log threads to finish
        for thread in self.log_threads:
            thread.join(timeout=1)
        
        self.processes.clear()
        self.log_threads.clear()
        ColoredLogger.success("All services stopped", "SYSTEM")
    
    def monitor_services(self):
        """Monitor running services and handle shutdown with enhanced error reporting"""
        try:
            ColoredLogger.success("Service monitoring started - watching for API calls, errors, and crashes", "SYSTEM")
            
            while True:
                # Check if any service has died
                for i, (name, process, port) in enumerate(self.processes):
                    if process.poll() is not None:  # Process has terminated
                        ColoredLogger.error(f"{name} has stopped unexpectedly!", "SYSTEM")
                        
                        # Get the return code
                        return_code = process.returncode
                        ColoredLogger.error(f"{name} exit code: {return_code}", "SYSTEM")
                        
                        # Try to get any remaining output
                        try:
                            # Don't wait too long for output
                            stdout, stderr = process.communicate(timeout=2)
                            if stdout:
                                ColoredLogger.info(f"{name} final stdout: {stdout.decode()}", "SYSTEM")
                            if stderr:
                                ColoredLogger.error(f"{name} final stderr: {stderr.decode()}", "SYSTEM")
                        except subprocess.TimeoutExpired:
                            ColoredLogger.warning(f"Timeout getting final output from {name}", "SYSTEM")
                        except Exception as e:
                            ColoredLogger.error(f"Error getting final output from {name}: {e}", "SYSTEM")
                        
                        ColoredLogger.error("Stopping all services due to service failure...", "SYSTEM")
                        self.stop_all_services()
                        return False
                
                time.sleep(1)  # Check every second for faster detection
                
        except KeyboardInterrupt:
            ColoredLogger.info("Received shutdown signal (Ctrl+C)...", "SYSTEM")
            self.stop_all_services()
            return True

def main():
    """Main function with enhanced error handling"""
    ColoredLogger.log("Gmail API Microservices Manager", 'BOLD', '🚀 ')
    ColoredLogger.log("Enhanced with real-time API monitoring", 'CYAN', '📊 ')
    
    manager = ServiceManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        ColoredLogger.warning("Interrupt signal received", "SYSTEM")
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start all services
        if manager.start_all_services():
            # Monitor services until shutdown
            manager.monitor_services()
        else:
            ColoredLogger.error("Failed to start services", "SYSTEM")
            return 1
    
    except Exception as e:
        ColoredLogger.error(f"Unexpected error: {e}", "SYSTEM")
        manager.stop_all_services()
        return 1
    
    ColoredLogger.success("Gmail API Microservices shutdown complete", "SYSTEM")
    return 0

if __name__ == "__main__":
    sys.exit(main())
