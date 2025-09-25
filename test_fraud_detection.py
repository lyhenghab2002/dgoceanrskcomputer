#!/usr/bin/env python3
"""
Test script for screenshot fraud detection
"""

import sys
import os
sys.path.append('.')

from utils.screenshot_fraud_detector import ScreenshotFraudDetector

def test_fraud_detection():
    """Test the fraud detection system"""
    detector = ScreenshotFraudDetector()
    
    print("🔍 Screenshot Fraud Detection Test")
    print("=" * 50)
    
    # Test with a sample image (if exists)
    test_image_path = "test_screenshot.jpg"
    
    if not os.path.exists(test_image_path):
        print("❌ Test image not found. Please add a test screenshot as 'test_screenshot.jpg'")
        print("\nTo test the system:")
        print("1. Add a payment screenshot as 'test_screenshot.jpg'")
        print("2. Run this script again")
        return
    
    print(f"📸 Testing with: {test_image_path}")
    
    # Test comprehensive verification
    result = detector.comprehensive_verification(
        test_image_path, 
        order_id=999,  # Test order ID
        expected_amount=100.00  # Test amount
    )
    
    print(f"\n📊 Verification Results:")
    print(f"   Fraud Detected: {'❌ YES' if result['is_fraud'] else '✅ NO'}")
    print(f"   Confidence Score: {result['confidence_score']:.2f}")
    
    if result['fraud_reasons']:
        print(f"\n🚨 Fraud Reasons:")
        for reason in result['fraud_reasons']:
            print(f"   - {reason}")
    
    print(f"\n🔍 Verification Details:")
    for check, passed in result['verification_details'].items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check}: {status}")
    
    print(f"\n💡 System Status: {'Fraud Detected' if result['is_fraud'] else 'Legitimate Screenshot'}")

if __name__ == "__main__":
    test_fraud_detection()
