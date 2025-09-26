#!/usr/bin/env python3
"""
Integration test script for Ambient Email Agent
Tests the complete workflow from email processing to HITL approval
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_environment():
    """Test environment setup"""
    print("🔍 Testing environment setup...")
    
    required_vars = ['GOOGLE_GENERATIVE_AI_API_KEY', 'HITL_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✅ Environment variables configured")
    return True

def test_services():
    """Test service imports and initialization"""
    print("🔍 Testing service imports...")
    
    try:
        from src.services.memory_store import init_db, get_profile
        from src.services.genai_service import classify_email, draft_reply
        from src.services.gmail_service import extract_sender_email
        from src.graph.build import build_graph
        
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Test profile retrieval
        profile = get_profile("test_user")
        print(f"✅ Profile system working: {profile['tone']}")
        
        # Test graph building
        graph = build_graph()
        print("✅ LangGraph built successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

def test_api_server():
    """Test API server endpoints"""
    print("🔍 Testing API server...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test health endpoint (if exists)
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print(f"⚠️ API server responded with status {response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ API server is not running")
        print("Please start the server with: uvicorn src.app:app --reload")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_email_processing():
    """Test email processing workflow"""
    print("🔍 Testing email processing workflow...")
    
    try:
        from src.services.genai_service import classify_email, draft_reply
        from src.services.memory_store import get_profile
        
        # Test email classification
        test_subject = "Meeting Request for Next Week"
        test_body = "Hi, can we schedule a meeting for next Tuesday at 2 PM? Thanks!"
        test_sender = "colleague@company.com"
        
        classification = classify_email(test_subject, test_body, test_sender)
        print(f"✅ Email classified as: {classification}")
        
        # Test draft generation
        profile = get_profile("test_user")
        draft = draft_reply(
            test_subject, 
            test_body, 
            profile["tone"], 
            profile["preferred_meeting_hours"],
            test_sender
        )
        print(f"✅ Draft generated: {draft[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Email processing test failed: {e}")
        return False

def test_graph_workflow():
    """Test complete LangGraph workflow"""
    print("🔍 Testing LangGraph workflow...")
    
    try:
        from src.graph.build import build_graph
        
        graph = build_graph()
        
        # Test state
        test_state = {
            "user_id": "test_user",
            "email_id": "test_123",
            "email_subject": "Test Email",
            "email_body": "This is a test email for integration testing",
            "email_sender": "test@example.com",
            "email_recipient": "user@example.com"
        }
        
        # Run the graph
        result = graph.invoke(test_state)
        print(f"✅ Graph workflow completed: {result.get('triage', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Graph workflow test failed: {e}")
        return False

def test_vip_contacts():
    """Test VIP contacts functionality"""
    print("🔍 Testing VIP contacts...")
    
    try:
        from src.services.memory_store import add_vip_contact, get_vip_contacts, is_vip_contact
        
        # Add VIP contact
        success = add_vip_contact("test_user", "boss@company.com", "My Boss", priority=2)
        if success:
            print("✅ VIP contact added")
        else:
            print("❌ Failed to add VIP contact")
            return False
        
        # Check VIP status
        is_vip = is_vip_contact("test_user", "boss@company.com")
        if is_vip:
            print("✅ VIP contact recognition working")
        else:
            print("❌ VIP contact recognition failed")
            return False
        
        # Get VIP contacts
        vip_contacts = get_vip_contacts("test_user")
        print(f"✅ VIP contacts retrieved: {len(vip_contacts)} contacts")
        
        return True
        
    except Exception as e:
        print(f"❌ VIP contacts test failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("🚀 Starting Ambient Email Agent Integration Tests\n")
    
    tests = [
        ("Environment Setup", test_environment),
        ("Service Imports", test_services),
        ("API Server", test_api_server),
        ("Email Processing", test_email_processing),
        ("Graph Workflow", test_graph_workflow),
        ("VIP Contacts", test_vip_contacts),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
