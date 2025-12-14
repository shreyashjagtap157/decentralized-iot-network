# Device Onboarding Guide

## Quick Start

Get your IoT device earning NWR tokens in 10 minutes!

---

## Prerequisites

### Hardware Requirements
- **ESP32** development board (recommended: ESP32-WROOM-32)
- USB cable for programming
- Stable internet connection

### Software Requirements
- [PlatformIO IDE](https://platformio.org/install/ide) or VS Code with PlatformIO extension
- Git (optional)

---

## Step 1: Download Firmware

### Option A: Pre-built Binary (Easiest)

1. Download the latest firmware from [releases](https://github.com/shreyashjagtap157/decentralized-iot-network/releases)
2. Use [ESP Web Flasher](https://web.esphome.io/) to flash directly from browser
3. Skip to Step 3

### Option B: Build from Source

```bash
# Clone repository
git clone https://github.com/shreyashjagtap157/decentralized-iot-network.git
cd decentralized-iot-network/device-firmware

# Build firmware
pio run -e esp32dev

# Flash to device
pio run -e esp32dev -t upload
```

---

## Step 2: Configure Device

### 2.1 Connect to Device AP

After flashing, your device creates a WiFi access point:

```
SSID: IoT-Network-Setup
Password: setup12345
```

### 2.2 Open Configuration Portal

1. Connect your phone/laptop to the device AP
2. Open browser: `http://192.168.4.1`
3. You'll see the setup wizard

### 2.3 Enter Configuration

| Field | Description |
|-------|-------------|
| **WiFi SSID** | Your home WiFi network name |
| **WiFi Password** | Your WiFi password |
| **Device Name** | Friendly name (e.g., "Living Room Node") |
| **API Key** | From mobile app or dashboard |
| **Wallet Address** | Your ETH/Polygon wallet for rewards |

### 2.4 Save and Reboot

Click "Save Configuration". Device will reboot and connect to your WiFi.

---

## Step 3: Register on Network

### 3.1 Install Mobile App

Download from:
- [iOS App Store](#)
- [Google Play Store](#)

### 3.2 Create Account

1. Open app and tap "Sign Up"
2. Connect your wallet (MetaMask, WalletConnect)
3. Verify email

### 3.3 Add Device

1. Go to "Devices" tab
2. Tap "+" to add device
3. Scan QR code on device (or enter Device ID)
4. Confirm registration

---

## Step 4: Start Earning

### 4.1 Activate Network Sharing

In the mobile app:
1. Select your device
2. Toggle "Share Network" ON
3. Device will start relaying traffic

### 4.2 Monitor Earnings

View real-time stats:
- 📊 Data transferred
- 💰 Pending rewards
- ⭐ Quality score
- 👥 Connected users

---

## LED Status Indicators

| LED Pattern | Status |
|-------------|--------|
| 🔴 Solid Red | No WiFi connection |
| 🟡 Blinking Yellow | Connecting to server |
| 🟢 Solid Green | Online, sharing network |
| 🔵 Blinking Blue | Data transfer active |
| 🟣 Purple | Mesh mode active |

---

## Troubleshooting

### Device won't connect to WiFi

1. Check WiFi credentials are correct
2. Ensure 2.4GHz network (5GHz not supported)
3. Move closer to router
4. Reset device: hold BOOT button 10 seconds

### Device not appearing in app

1. Wait 2-3 minutes for registration
2. Check internet connection
3. Verify API key is correct
4. Restart app

### Low quality score

1. Improve internet connection
2. Place device in central location
3. Reduce other network traffic
4. Upgrade internet plan

### Not receiving rewards

1. Ensure wallet address is correct
2. Check minimum payout threshold (100 NWR)
3. Wait for reward distribution (hourly)
4. Verify device is active and sharing

---

## Advanced Configuration

### Via Serial Console

Connect USB and open serial monitor at 115200 baud:

```
Commands:
  status      - Show device status
  restart     - Restart device
  reset       - Factory reset
  wifi SSID PASSWORD - Set WiFi
  api KEY     - Set API key
  wallet ADDR - Set wallet address
  mesh on/off - Toggle mesh mode
```

### Configuration File

Edit `config.json` on device filesystem:

```json
{
  "wifi_ssid": "YourNetwork",
  "wifi_password": "password",
  "api_endpoint": "https://api.iot-network.io",
  "api_key": "your_api_key",
  "wallet": "0x...",
  "mesh_enabled": true,
  "share_bandwidth_percent": 80
}
```

---

## Security Best Practices

1. ✅ Use strong WiFi password
2. ✅ Keep firmware updated
3. ✅ Use hardware wallet for large earnings
4. ✅ Enable 2FA on mobile app
5. ❌ Never share your API key
6. ❌ Don't expose device to public internet

---

## Getting Help

- 📖 [Full Documentation](https://docs.iot-network.io)
- 💬 [Discord Community](https://discord.gg/iot-network)
- 🐛 [Report Issues](https://github.com/shreyashjagtap157/decentralized-iot-network/issues)
- 📧 [Email Support](mailto:support@iot-network.io)

---

## Earning Calculator

| Internet Speed | Est. Monthly Earnings | Annual |
|----------------|----------------------|--------|
| 50 Mbps | ~500 NWR | 6,000 NWR |
| 100 Mbps | ~1,200 NWR | 14,400 NWR |
| 500 Mbps | ~4,000 NWR | 48,000 NWR |
| 1 Gbps | ~7,000 NWR | 84,000 NWR |

*Estimates based on average network usage and quality score of 80+*

---

## Next Steps

After your device is online:

1. 🎯 **Stake NWR** to boost earnings up to 3x
2. 🔗 **Add more devices** for more rewards
3. 🗳️ **Vote on governance** proposals
4. 🌍 **View coverage map** to see global network

Welcome to the decentralized internet! 🚀
