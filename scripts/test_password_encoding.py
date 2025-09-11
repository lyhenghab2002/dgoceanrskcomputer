#!/usr/bin/env python3
import urllib.parse

# Test password encoding
password = "YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc"
encoded_password = urllib.parse.quote_plus(password)

print("Original password:", password)
print("URL encoded password:", encoded_password)

# Test if they're different
if password != encoded_password:
    print("⚠️ Password needs URL encoding!")
else:
    print("✅ Password doesn't need URL encoding")
