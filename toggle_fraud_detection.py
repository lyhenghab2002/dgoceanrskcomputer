#!/usr/bin/env python3
"""
Toggle fraud detection on/off
"""

import sys
sys.path.append('.')

def toggle_fraud_detection(enabled=True):
    """Toggle fraud detection system"""
    from utils.screenshot_fraud_detector import ScreenshotFraudDetector
    
    # Update the global instance
    global screenshot_detector
    screenshot_detector = ScreenshotFraudDetector(enabled=enabled)
    
    status = "ENABLED" if enabled else "DISABLED"
    print(f"🔧 Fraud detection system is now {status}")
    
    return screenshot_detector

if __name__ == "__main__":
    if len(sys.argv) > 1:
        enabled = sys.argv[1].lower() in ['true', '1', 'yes', 'on', 'enable']
    else:
        enabled = True
    
    toggle_fraud_detection(enabled)
