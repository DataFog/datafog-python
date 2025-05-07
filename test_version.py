#!/usr/bin/env python

# Read version directly from __about__.py
with open('datafog/__about__.py', 'r') as f:
    about_content = f.read().strip()
    about_version = about_content.split('"')[1]  # Simple string split to extract version

print(f"Version in __about__.py: {about_version}")

# Read version from setup.py using the same method setup.py uses
about = {}
with open("datafog/__about__.py", "r") as f:
    exec(f.read(), about)

setup_version = about['__version__']
print(f"Version extracted by setup.py: {setup_version}")

# Verify they match
if about_version == setup_version:
    print("✅ SUCCESS: Single source of truth is working correctly!")
else:
    print("❌ ERROR: Versions don't match")
