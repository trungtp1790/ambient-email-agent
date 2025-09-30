#!/usr/bin/env python3
"""
Test script to verify JSON-based email classification
"""

import sys
import os
sys.path.append('src')

from services.genai_service import classify_email

def test_json_classification():
    """Test the JSON-based email classification"""
    
    # Test cases
    test_cases = [
        {
            "subject": "Meeting tomorrow at 2 PM",
            "body": "Hi, can we schedule a meeting for tomorrow at 2 PM? Let me know if that works for you.",
            "sender": "colleague@company.com",
            "expected": "schedule"
        },
        {
            "subject": "Please confirm the order",
            "body": "Hi, I need you to confirm the order details before we proceed. Can you please reply?",
            "sender": "client@customer.com", 
            "expected": "needs_reply"
        },
        {
            "subject": "Weekly Newsletter",
            "body": "Here's our weekly newsletter with the latest updates and news.",
            "sender": "newsletter@company.com",
            "expected": "fyi"
        },
        {
            "subject": "Win $1000 now!",
            "body": "Congratulations! You've won $1000! Click here to claim your prize!",
            "sender": "spam@fake.com",
            "expected": "spam"
        }
    ]
    
    print("🧪 Testing JSON-based email classification...")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📧 Test {i}: {test['subject']}")
        print(f"From: {test['sender']}")
        print(f"Expected: {test['expected']}")
        
        try:
            result = classify_email(
                test['subject'], 
                test['body'], 
                test['sender']
            )
            
            status = "✅ PASS" if result == test['expected'] else "❌ FAIL"
            print(f"Result: {result} {status}")
            
            if result != test['expected']:
                print(f"Expected: {test['expected']}, Got: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Test completed!")

if __name__ == "__main__":
    test_json_classification()
