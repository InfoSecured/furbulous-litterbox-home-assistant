# Furbulous Cat - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/fabienbounoir/furbulous-litterbox-home-assistant.svg)](https://github.com/fabienbounoir/furbulous-litterbox-home-assistant/releases)
[![HomeKit Compatible](https://img.shields.io/badge/HomeKit-Compatible-blue.svg)](docs/HOMEKIT_COMPATIBILITY.md)

Full integration for **Furbulous Cat** smart litter boxes in Home Assistant with HomeKit support.

---

## 🎯 Features

### ✅ Version 1.0.0
- ✅ **Authentication** - Login with email/password or direct token
- ✅ **Device Discovery** - Automatic litter box detection
- ✅ **22 Sensors** - Weight, uses, status, modes, versions, pet info, etc.
- ✅ **10 Binary Sensors** - Connectivity, errors, modes, cat in litter box
- ✅ **4 Buttons** - Cleaning, emptying, packing, DND
- ✅ **4 Switches** - HomeKit controls (auto clean, full auto mode, DND, child lock)
- ✅ **Pet Sensors** - Complete information for each cat
- ✅ **Error Detection** - 11 error codes with severity
- ✅ **Fast Updates** - Cat in litter box: **30 seconds** / Others: 5 minutes
- ✅ **HomeKit Support** - Compatible with HomeKit Bridge + Siri
- ✅ **Auto Token Refresh** - Automatic token renewal

### 📊 Total: ~40 entities per installation
- 22 sensors (status, weight, uses, versions, pet info, etc.)
- 10 binary_sensors (connectivity, modes, errors, cat presence)
- 4 buttons (manual control)
- 4 switches (HomeKit control)
- 1+ pet sensors (one per cat)

---

## 📦 Installation

### Option 1: HACS (Recommended)

1. **Open HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **3 dots** top right → **Custom repositories**
4. Add URL: `https://github.com/fabienbounoir/furbulous-litterbox-home-assistant`
5. Category: **Integration**
6. Search for "Furbulous Cat"
7. Click **Download**
8. Restart Home Assistant

### Option 2: Manual installation

1. **Copy files**
   ```bash
   cd /path/to/homeassistant/config
   mkdir -p custom_components
   cp -r custom_components/furbulous custom_components/
   ```

2. **Restart Home Assistant**
   - Via UI: **Settings** → **System** → **Restart**

### Configuration

1. **Add the integration**
   - **Settings** → **Devices & Services** → **Add Integration**
   - Search "Furbulous Cat"
   - Enter email + password (Furbulous account)

2. **HomeKit (Optional)**
   - See [HOMEKIT_COMPATIBILITY.md](docs/HOMEKIT_COMPATIBILITY.md)
   - Expose recommended switches and binary sensors
   - Control with Siri and Home app

---

## 📊 Main Entities

### 🔘 Switches (HomeKit Compatible)
- `switch.furbulous_box_automatic_cleaning` - Auto clean after use
- `switch.furbulous_box_full_auto_mode` - Full auto mode
- `switch.furbulous_box_do_not_disturb` - Silent mode (night)
- `switch.furbulous_box_child_lock` - Child safety lock

### 🔴 Binary Sensors
- ⭐ `binary_sensor.furbulous_box_cat_in_litter_box` - Cat detection (**30s**)
- `binary_sensor.furbulous_box_connected` - Connection status
- `binary_sensor.furbulous_box_error` - Error detection
- `binary_sensor.furbulous_box_waste_bin_full` - Waste bin full

### 📊 Sensors
- `sensor.furbulous_box_cat_weight` - Weight in grams
- `sensor.furbulous_box_daily_uses` - Number of uses
- `sensor.furbulous_box_operating_status` - Status (Idle/Working/Cleaning)
- `sensor.furbulous_box_error` - Detailed error code
- `sensor.furbulous_cat_<name>` - Cat info (age, weight, breed)

### 🔘 Buttons
- `button.furbulous_box_manual_clean` - Manual cleaning
- `button.furbulous_box_empty` - Empty the bin
- `button.furbulous_box_auto_pack` - Automatic packing

[📖 Full list of 40+ entities](docs/INSTALLATION.md)

---

## 🏠 HomeKit

The integration is **100% compatible** with HomeKit Bridge:

✅ **4 switches** - Full control via Siri and Home app  
✅ **Binary sensor cat** - Presence detection every 30 seconds  
✅ **Binary sensors alerts** - Errors, bin full, connection  

**Siri commands:**
- *"Hey Siri, turn on automatic cleaning"*
- *"Hey Siri, is the cat in the litter box?"*

[📖 Full HomeKit guide](docs/HOMEKIT_COMPATIBILITY.md)

---

## 🎨 Automation Examples

### Cat presence notification
```yaml
automation:
  - alias: "Cat detected in litter box"
    trigger:
      platform: state
      entity_id: binary_sensor.furbulous_box_cat_in_litter_box
      to: 'on'
    action:
      service: notify.mobile_app
      data:
        message: "🐱 Milo is using the litter box"
```

### Night DND
```yaml
automation:
  - alias: "Night DND"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      service: switch.turn_on
      target:
        entity_id: switch.furbulous_box_do_not_disturb
```

### Waste bin full alert
```yaml
automation:
  - alias: "Waste bin full"
    trigger:
      platform: state
      entity_id: binary_sensor.furbulous_box_waste_bin_full
      to: 'on'
    action:
      service: notify.mobile_app
      data:
        title: "🗑️ Furbulous"
        message: "The waste bin is full - Please empty it now"
```

[📖 More examples](docs/EXAMPLES.md)

---

## 🔄 Updates

| Interval | Affected Entities |
|------------|-------------------|
| **30 seconds** | Cat in litter box (binary_sensor) |
| **5 minutes** | All other sensors |

The cat presence sensor uses a **fast coordinator** for near real-time detection.

---

## 🔍 Error Codes

| Code | Message | Severity |
|------|---------|----------|
| 0 | No error | info |
| 1 | Weight sensor error | warning |
| 2 | IR sensor error | warning |
| 4 | Motor blocked | error |
| 8 | Motor overload | error |
| 16 | Litter full | warning |
| 32 | Normal operation | info |
| 64 | Drawer not in place | warning |
| 128 | Cover open | warning |
| 256 | Temperature error | error |
| 512 | Communication error | error |

---

## 📚 Documentation

- **[INSTALLATION.md](docs/INSTALLATION.md)** - Detailed installation guide
- **[API_ENDPOINTS.md](docs/API_ENDPOINTS.md)** - 86 documented API endpoints

---

## 🤝 Contributing

Contributions are welcome! 

1. Fork the project  
2. Create a branch (`git checkout -b feature/amazing`)  
3. Commit your changes (`git commit -m 'Add amazing feature'`)  
4. Push (`git push origin feature/amazing`)  
5. Open a Pull Request

---

## 📄 License

This project is licensed under MIT - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- Furbulous API for the smart litter box  
- Home Assistant community  
- All contributors

---

**Version**: 1.0.0  
**Status**: ✅ Production Ready  
**Author**: [@fabienbounoir](https://github.com/fabienbounoir)  
**HomeKit**: ✅ Compatible  
**HACS**: ✅ Supported
