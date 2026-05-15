# ANA MAX - Licensing Guide

## Overview

ANA MAX uses a licensing system to differentiate between **Free (Trial)** and **Pro** features. This guide explains how the licensing works and how to activate a Pro license.

## Free vs Pro Features

### Free (Trial) Version
The free version includes **42 functional tools**:
- All code tools (edit, search, understanding)
- Web tools (browser, scraper, search)
- System tools (terminal, control, optimization)
- Security tools (audit, pentest, network)
- UI Automation (`windows_uia_bridge`)
- Git operations
- File operations
- And more...

### Pro Version (License Required)
The Pro version unlocks **5 additional premium tools**:
- `desktop_capture` - AI screenshot capture
- `live_desktop_viewer` - Real-time desktop streaming
- `desktop_control` - Full desktop automation
- `windows_insight` - Advanced system monitoring
- `windows_deep_sight` - "God View" system analysis

## How to Activate a Pro License

### Method 1: Using Python Command

```bash
python -c "from core.license_manager import LicenseManager; m = LicenseManager(); m.activate('YOUR_LICENSE_KEY_HERE')"
```

### Method 2: Using the activate_license.py Script

```bash
python activate_license.py --key YOUR_LICENSE_KEY_HERE
```

### Method 3: Manual File Placement

Place your license key in a file named `.license` in the ANA MAX root directory.

## License Types

### Trial License
- Duration: Up to 7 days
- Full access to all Pro features
- Perfect for testing before purchasing

### Pro License
- Duration: 30 days, 90 days, 1 year, or lifetime
- Full access to all Pro features
- Email-based activation

## Checking License Status

### Via Command Line
```bash
python -c "from core.license_manager import get_license_manager; m = get_license_manager(); print(m.get_license_info())"
```

### Via MCP Protocol
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "license.status",
  "params": {}
}
```

### Via REST API
```
GET http://127.0.0.1:8765/health
```

The response will include the license type:
```json
{
  "status": "online",
  "license": "pro",
  ...
}
```

## For Developers: Generating Licenses

If you need to generate licenses (e.g., for distribution), use the `generate_license.py` script:

```bash
# Generate a 30-day Pro license
python generate_license.py --email user@example.com --days 30

# Generate a 7-day trial license
python generate_license.py --email user@example.com --days 7 --trial

# Output only the key (for scripting)
python generate_license.py --email user@example.com --days 30 --quiet
```

## License File Format

The `.license` file contains encrypted JSON data:
```json
{
  "email": "user@example.com",
  "issued": "2026-05-15T10:30:00",
  "expires": "2026-06-14T10:30:00",
  "type": "pro",
  "version": "1.0",
  "activated": "2026-05-15T10:35:00",
  "machine_id": "abc123def456..."
}
```

## Security Features

- **Encryption**: License data is encrypted using Fernet (AES-128 in CBC mode)
- **Signature**: HMAC-SHA256 signature prevents tampering
- **Machine Binding**: License is bound to the machine's hardware ID
- **Expiration Check**: Automatic validation on every premium tool access

## Troubleshooting

### License Not Working

1. **Check expiration**: Ensure your license hasn't expired
2. **Check machine ID**: License is bound to the original machine
3. **Re-activate**: Try activating again with the same key

### Premium Tools Still Blocked

1. **Restart server**: After activation, restart the MCP server
2. **Check license status**: Verify the license is loaded correctly
3. **File permissions**: Ensure `.license` file is readable

### Generating License on Different Machine

The license is bound to the machine where it was activated. If you need to use it on a different machine, you'll need to:
1. Deactivate on the old machine: `python -c "from core.license_manager import get_license_manager; m = get_license_manager(); m.deactivate()"`
2. Activate on the new machine with the same key

## API Reference

### LicenseManager Class

```python
from core.license_manager import LicenseManager, get_license_manager, check_premium_access

# Get the global manager
manager = get_license_manager()

# Check if a tool is allowed
allowed, message = check_premium_access("desktop_capture")

# Get license info
info = manager.get_license_info()
# Returns: {"type": "pro", "email": "...", "expires": "...", "is_valid": True, "days_remaining": 25}

# Check if Pro
is_pro = manager.is_pro()

# Activate a license
success, message = manager.activate("LICENSE_KEY")

# Deactivate
manager.deactivate()
```

## Purchasing a License

To purchase a Pro license, visit: https://github.com/gyodragos-cell/ANA-MAX

## Support

For licensing issues, please open an issue at:
https://github.com/gyodragos-cell/ANA-MAX/issues