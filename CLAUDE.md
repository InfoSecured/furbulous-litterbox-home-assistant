# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Assistant custom integration** for Furbulous Cat smart litter boxes. It's a HACS-compatible integration that provides device control, monitoring, and HomeKit compatibility.

**Key characteristics:**
- Cloud-based IoT integration (polling)
- Dual-coordinator architecture (fast + slow polling)
- HomeKit-compatible switches and sensors
- Token-based or email/password authentication

## Type Checking

This project uses mypy for type checking. Run type checks with:

```bash
/Users/J.Lazerus_1/Library/Python/3.11/bin/mypy custom_components/furbulous --ignore-missing-imports
```

Or if mypy is in your PATH:

```bash
mypy custom_components/furbulous --ignore-missing-imports
```

**Type hints:**
- Use `from __future__ import annotations` at the top of all files
- Use modern type hints: `str | None` instead of `Optional[str]`
- Use `dict[str, Any]` instead of `Dict[str, Any]`
- For Home Assistant config flow: use `# type: ignore[call-arg]` on the ConfigFlow class definition (the `domain=` parameter is HA-specific)

## Architecture

### Dual-Coordinator System

The integration uses **two DataUpdateCoordinators** in `__init__.py`:

1. **Regular Coordinator** (`FurbulousCatDataUpdateCoordinator`)
   - Update interval: 5 minutes
   - Used by: sensors, switches, buttons
   - Purpose: General device data, properties, pet info

2. **Fast Coordinator** (`FurbulousCatFastUpdateCoordinator`)
   - Update interval: 30 seconds
   - Used by: `FurbulousCatInBoxSensor` binary sensor only
   - Purpose: Near real-time cat presence detection

**Why two coordinators?** Home Assistant best practice is to avoid excessive API calls. Most data doesn't change frequently, but cat presence detection needs faster updates for useful automations.

### Platform Architecture

Each platform follows Home Assistant's standard pattern:

- **`sensor.py`**: 22+ sensors (weight, usage, status, versions, pet info)
- **`binary_sensor.py`**: 10 binary sensors (connectivity, modes, errors, cat presence)
- **`button.py`**: 4 action buttons (manual clean, empty, auto-pack, DND)
- **`switch.py`**: 4 switches (HomeKit-compatible controls)

All entity classes inherit from `CoordinatorEntity` to automatically handle data updates.

### API Client (`furbulous_api.py`)

**Authentication flow:**
1. User can provide either:
   - Email + password (will authenticate and get token)
   - Direct token (bypasses authentication)
2. Token is stored and used for all subsequent requests
3. Auto-retry logic: if API returns token error, re-authenticate and retry once

**Signature generation:**
- All API requests require an HMAC-style signature: `MD5(appid + endpoint + timestamp)`
- Signature is calculated on the endpoint path WITHOUT query parameters
- Headers include: `appid`, `version`, `platform`, `ts`, `sign`, `authorization` (token)

**Important methods:**
- `authenticate()`: Login and get token
- `get_devices()`: Fetch all devices
- `get_device_properties(iotid)`: Get device properties (returns extracted values)
- `set_device_property(iotid, properties)`: Set device properties (switches, buttons)
- `set_device_disturb(iotid, is_disturb)`: Toggle DND mode
- `get_pets()`: Fetch pet list
- `get_data()`: Main method called by coordinators - returns combined device + pet data

### Device Info Helper (`device.py`)

The `get_device_info()` function creates Home Assistant DeviceInfo dictionaries. All entities use this to ensure they're grouped under the same device in the UI.

**Device identifiers:** Uses `(DOMAIN, str(device_id))` tuple for unique device identification.

### Constants (`const.py`)

Contains:
- API endpoints and authentication headers
- Work status mappings (Idle, Working, Cleaning, etc.)
- Error code mappings (11 error types with severity levels)
- Litter type mappings
- Configuration constants

**Error severity levels:** `info`, `warning`, `error` - used by binary sensor to determine alert priority.

## Home Assistant Integration Patterns

### Config Flow (`config_flow.py`)

Supports two authentication modes:
1. **Token mode**: User provides token directly (useful for advanced users)
2. **Email/password mode**: Standard login flow

**Validation:** Tests authentication by calling `api.get_devices()` or `api.authenticate()`

**Unique ID:** Uses email or token prefix to prevent duplicate entries

### Entity Naming Convention

Format: `{device_name} - {entity_description}`

Examples:
- `Furbulous Box - Cat weight`
- `Furbulous Box - Automatic cleaning`
- `Furbulous Cat - {pet_name}`

### Property Handling

Many entities read from `device["properties"]` dictionary. Properties can be:
- Direct values: `properties["key"] = 123`
- Value/time dicts: `properties["key"] = {"value": 123, "time": 1234567890}`

Always check both formats when reading properties (see sensor.py line 274-277).

## API Behavior Notes

### Token Refresh

The API may return error codes or messages indicating token expiration:
- Error codes: 401, 10401, 10402
- Error messages containing: "token", "Token", "无效的" (Chinese for "invalid")

When detected, the client automatically re-authenticates and retries the request once.

### Property Setting

Use `set_device_property(iotid, {property_name: value})` for most controls:
- `catCleanOnOff`: 0/1 (auto cleaning)
- `FullAutoModeSwitch`: 0/1 (full auto mode)
- `childLockOnOff`: 0/1 (child lock)
- `handMode`: 1 (clean), 2 (dump), 3 (auto-pack)

Use `set_device_disturb(iotid, is_disturb)` specifically for DND mode.

## HomeKit Compatibility

The integration is designed for HomeKit Bridge compatibility. The 4 switches in `switch.py` are specifically designed to work well with HomeKit:
- Auto cleaning switch
- Full auto mode switch
- DND switch
- Child lock switch

Binary sensors also expose well to HomeKit for automations.

## Testing Changes

**Manual testing in Home Assistant:**
1. Copy changes to your HA config: `config/custom_components/furbulous/`
2. Restart Home Assistant
3. Check logs: `config/home-assistant.log` or via UI (Settings → System → Logs)

**Debug logging:** Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.furbulous: debug
```

## Common Patterns

### Adding a New Sensor

1. Add entity class to appropriate platform file
2. Inherit from `CoordinatorEntity` and the sensor type
3. Set `_attr_unique_id`, `_attr_name`, `_attr_device_info`
4. Implement property accessors that read from `self.coordinator.data`
5. Add instantiation in `async_setup_entry()`

### Adding a New Device Property

1. Update mappings in `const.py` if needed (status codes, etc.)
2. Add sensor in `sensor.py` or binary sensor in `binary_sensor.py`
3. If it's controllable, add switch in `switch.py` or button in `button.py`

### Handling API Errors

The API client handles most errors automatically. For new API calls:
- Use `_make_authenticated_request()` for authenticated endpoints
- It handles token refresh automatically
- Returns parsed JSON response
- Check `response["code"] == 0` for success

## Version Information

- **Current version:** 1.2.0 (see `manifest.json`)
- **Home Assistant requirements:** See `manifest.json` for dependencies
- **Python version:** Compatible with Python 3.11+

## Documentation

Extensive documentation is available in `docs/`:
- `API_ENDPOINTS.md`: 86+ documented API endpoints
- `API_DOCUMENTATION.md`: Complete API documentation
- `INSTALLATION.md`: User installation guide
- `HOMEKIT_COMPATIBILITY.md`: HomeKit setup guide
- `IMPLEMENTATION_SUMMARY.md`: Technical implementation details

Refer to these docs when implementing new features or understanding API behavior.
