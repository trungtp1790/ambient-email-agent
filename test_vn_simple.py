#!/usr/bin/env python3
"""
Test đơn giản cho email tiếng Việt
"""

import os
import sys
# Add src to path
sys.path.append('src')

from services.genai_service import classify_email

def test_vn_emails():
    """Test một vài email tiếng Việt cơ bản"""
    
    test_cases = [
        {
            "subject": "Họp team tuần tới",
            "body": "Chào mọi người, chúng ta có cuộc họp team vào thứ 3 tuần tới lúc 2h chiều.",
            "sender": "manager@congty.com",
            "expected": "schedule"
        },
        {
            "subject": "Cần phản hồi gấp",
            "body": "Dự án deadline sắp tới rồi. Anh có thể review và gửi feedback trước 5h chiều nay được không?",
            "sender": "pm@congty.com",
            "expected": "needs_reply"
        },
        {
            "subject": "Chúc mừng! Bạn đã trúng thưởng!",
            "body": "Chúc mừng! Bạn đã trúng 10 triệu đồng! Nhấn vào đây để nhận thưởng ngay!",
            "sender": "lottery@fake.com",
            "expected": "spam"
        }
    ]
    
    print("🇻🇳 Testing Vietnamese emails...")
    print("=" * 50)
    
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
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    test_vn_emails()
