#!/usr/bin/env python3
"""
Development startup script for Ambient Email Agent
Starts both API server and background worker
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment...")
    
    # Check .env file
    if not Path(".env").exists():
        print("❌ .env file not found. Please copy .env.example to .env and configure it.")
        return False
    
    # Check required environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['GOOGLE_GENERATIVE_AI_API_KEY', 'HITL_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✅ Environment configured")
    return True

def check_credentials():
    """Check if Gmail credentials are available"""
    print("🔍 Checking Gmail credentials...")
    
    if not Path("credentials/credentials.json").exists():
        print("❌ Gmail credentials not found.")
        print("Please download credentials.json from Google Cloud Console")
        print("and place it in the credentials/ folder")
        return False
    
    if not Path("token.json").exists():
        print("⚠️ Gmail token not found. You may need to run:")
        print("python -c \"from src.services.gmail_service import bootstrap_token; bootstrap_token()\"")
        print("This will open a browser for OAuth authentication.")
        
        response = input("Do you want to generate the token now? (y/n): ")
        if response.lower() == 'y':
            try:
                from src.services.gmail_service import bootstrap_token
                bootstrap_token()
                print("✅ Gmail token generated")
            except Exception as e:
                print(f"❌ Failed to generate token: {e}")
                return False
        else:
            print("⚠️ Continuing without Gmail token (some features may not work)")
    
    print("✅ Gmail credentials ready")
    return True

def start_api_server():
    """Start the FastAPI server"""
    print("🚀 Starting API server...")
    
    try:
        # Start uvicorn server
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "src.app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ API server started on http://localhost:8000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ API server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def start_worker():
    """Start the background worker"""
    print("🚀 Starting background worker...")
    
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "src.ambient_loop"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for worker to start
        time.sleep(2)
        
        if process.poll() is None:
            print("✅ Background worker started")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Background worker failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start background worker: {e}")
        return None

def monitor_processes(api_process, worker_process):
    """Monitor running processes"""
    print("\n🔄 Monitoring processes...")
    print("Press Ctrl+C to stop all services")
    
    try:
        while True:
            # Check if processes are still running
            if api_process and api_process.poll() is not None:
                print("❌ API server stopped unexpectedly")
                break
                
            if worker_process and worker_process.poll() is not None:
                print("❌ Background worker stopped unexpectedly")
                break
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        
        if api_process:
            api_process.terminate()
            print("✅ API server stopped")
            
        if worker_process:
            worker_process.terminate()
            print("✅ Background worker stopped")
        
        print("👋 Goodbye!")

def main():
    """Main startup function"""
    print("🤖 Ambient Email Agent - Development Mode")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check credentials
    if not check_credentials():
        print("⚠️ Continuing with limited functionality...")
    
    # Start services
    api_process = start_api_server()
    if not api_process:
        print("❌ Failed to start API server. Exiting.")
        sys.exit(1)
    
    worker_process = start_worker()
    if not worker_process:
        print("⚠️ Background worker failed to start. API server is still running.")
    
    print("\n" + "=" * 50)
    print("🎉 Services started successfully!")
    print("📱 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    
    # Monitor processes
    monitor_processes(api_process, worker_process)

if __name__ == "__main__":
    main()
