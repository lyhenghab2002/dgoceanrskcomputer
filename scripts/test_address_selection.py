#!/usr/bin/env python3
"""
Test script to check address selection functionality
"""

import requests
import json

# Test the address selection API
def test_address_selection():
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Check if addresses are being loaded
    print("=== Testing Address Loading ===")
    try:
        response = requests.get(f"{base_url}/api/customer/addresses")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Addresses loaded successfully: {len(data.get('addresses', []))} addresses")
            for addr in data.get('addresses', []):
                print(f"  - ID: {addr.get('id')}, Type: {addr.get('address_type')}, Street: {addr.get('street_name')}")
        else:
            print(f"❌ Failed to load addresses: {response.status_code}")
    except Exception as e:
        print(f"❌ Error loading addresses: {e}")
    
    # Test 2: Check a specific address
    print("\n=== Testing Specific Address ===")
    try:
        response = requests.get(f"{base_url}/api/customer/addresses/1")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Address 1 loaded: {data}")
        else:
            print(f"❌ Failed to load address 1: {response.status_code}")
    except Exception as e:
        print(f"❌ Error loading address 1: {e}")

if __name__ == "__main__":
    test_address_selection()
