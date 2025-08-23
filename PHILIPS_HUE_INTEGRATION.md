# Philips Hue Integration & Commissioning

This document describes the comprehensive Philips Hue integration and commissioning capabilities implemented in the IoT platform.

## Overview

The Philips Hue integration provides full support for:
- **Bridge Discovery**: Automatic discovery of Hue bridges on the network
- **Bridge Pairing**: Secure pairing with Hue bridges
- **Device Discovery**: Automatic discovery of all connected Hue lights
- **Device Commissioning**: Complete device onboarding and configuration
- **Capability Control**: Full control of Hue lights (switch, dim, color, temperature)
- **Workflow Management**: End-to-end commissioning workflows

## Architecture

### Components

1. **Hue Capability Adapters** (`iot-api-discovery/tools/hue/adapters.py`)
   - `HueSwitchAdapter`: Basic on/off control
   - `HueDimmableAdapter`: Brightness control
   - `HueColorControlAdapter`: Color and temperature control

2. **Hue Commissioning Service** (`iot-api-discovery/tools/hue/commissioning.py`)
   - Bridge discovery and pairing
   - Device discovery and analysis
   - Device commissioning and testing

3. **Hue Commissioning API** (`iot-api-discovery/api/hue_commissioning.py`)
   - REST API endpoints for Hue operations
   - Bridge and device management

4. **Hue Onboarding Workflow** (`services/connection/onboarding/hue_workflow.py`)
   - Specialized onboarding workflow for Hue devices
   - Step-by-step commissioning process

5. **Commissioning API** (`services/connection/commissioning_api.py`)
   - Generic commissioning endpoints
   - Multi-provider support

## Quick Start

### 1. Discover Hue Bridges

```bash
curl -X POST "http://localhost:8000/hue/discover-bridges" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"network_range": "192.168.1.0/24"}'
```

Response:
```json
{
  "ok": true,
  "bridges": [
    {
      "id": "hue_bridge_1",
      "ip_address": "192.168.1.100",
      "port": 80,
      "discovery_method": "cloud",
      "status": "discovered"
    }
  ],
  "count": 1,
  "message": "Discovered 1 Hue bridge(s)"
}
```

### 2. Pair with Bridge

```bash
curl -X POST "http://localhost:8000/hue/pair-bridge" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "bridge_ip": "192.168.1.100",
    "app_name": "iot-orchestrator",
    "device_name": "server"
  }'
```

**Important**: Press the link button on the Hue bridge before pairing.

Response:
```json
{
  "ok": true,
  "bridge_id": "hue_192_168_1_100",
  "username": "abc123def456",
  "message": "Bridge paired successfully"
}
```

### 3. Discover Devices

```bash
curl -X GET "http://localhost:8000/hue/bridges/hue_192_168_1_100/devices" \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "ok": true,
  "bridge_id": "hue_192_168_1_100",
  "devices": [
    {
      "device_id": "hue_192_168_1_100:1",
      "bridge_id": "hue_192_168_1_100",
      "light_id": "1",
      "name": "Living Room Light",
      "type": "Extended color light",
      "model_id": "LCT001",
      "manufacturer": "Philips",
      "capabilities": ["switchable", "dimmable", "color_control"],
      "provider": "hue",
      "discovered_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1,
  "message": "Discovered 1 device(s) on bridge hue_192_168_1_100"
}
```

### 4. Control Devices

#### Turn On/Off
```bash
curl -X POST "http://localhost:8000/capability/hue/hue_192_168_1_100:1/switch/on" \
  -H "X-API-Key: your-api-key"
```

#### Set Brightness
```bash
curl -X POST "http://localhost:8000/capability/hue/hue_192_168_1_100:1/dimmer/set" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"level": 75}'
```

#### Set Color (HSV)
```bash
curl -X POST "http://localhost:8000/capability/hue/hue_192_168_1_100:1/color/hsv" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"h": 120, "s": 1.0, "v": 1.0}'
```

#### Set Color Temperature
```bash
curl -X POST "http://localhost:8000/capability/hue/hue_192_168_1_100:1/color/temp" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"mireds": 300}'
```

## Commissioning Workflow

### Start Hue Commissioning

```bash
curl -X POST "http://localhost:8000/commissioning/hue/start" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "bridge_ip": "192.168.1.100",
    "app_name": "iot-orchestrator",
    "device_name": "server"
  }'
```

Response:
```json
{
  "ok": true,
  "workflow_id": "hue_onboarding_192_168_1_100_1705312200",
  "bridge_ip": "192.168.1.100",
  "status": "started",
  "message": "Hue commissioning workflow started"
}
```

### Monitor Workflow Status

```bash
curl -X GET "http://localhost:8000/commissioning/status/hue_onboarding_192_168_1_100_1705312200" \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "ok": true,
  "workflow_id": "hue_onboarding_192_168_1_100_1705312200",
  "status": {
    "id": "hue_onboarding_192_168_1_100_1705312200",
    "device_name": "Philips Hue Bridge (192.168.1.100)",
    "current_step": "device_commissioning",
    "status": "running",
    "steps_completed": [
      "bridge_discovery",
      "bridge_pairing",
      "bridge_connected",
      "device_discovery",
      "device_analysis"
    ],
    "steps_failed": [],
    "start_time": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T10:35:00Z",
    "error": null,
    "bridge_ip": "192.168.1.100",
    "bridge_id": "hue_192_168_1_100",
    "discovered_devices_count": 3,
    "commissioned_devices_count": 2,
    "discovered_devices": [...],
    "commissioned_devices": [...]
  }
}
```

## API Endpoints

### Hue Commissioning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/hue/discover-bridges` | Discover Hue bridges on network |
| POST | `/hue/pair-bridge` | Pair with a Hue bridge |
| GET | `/hue/bridges` | List paired bridges |
| GET | `/hue/bridges/{bridge_id}/devices` | Discover devices on bridge |
| POST | `/hue/devices/test` | Test device communication |
| POST | `/hue/devices/commission` | Commission a device |
| GET | `/hue/status` | Get commissioning status |
| DELETE | `/hue/bridges/{bridge_id}` | Remove a bridge |
| POST | `/hue/bridges/{bridge_id}/refresh` | Refresh device list |
| GET | `/hue/devices` | List all devices |
| GET | `/hue/devices/{device_id}` | Get device info |

### Generic Commissioning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/commissioning/start` | Start generic commissioning |
| POST | `/commissioning/hue/start` | Start Hue commissioning |
| GET | `/commissioning/status/{workflow_id}` | Get workflow status |
| GET | `/commissioning/workflows` | List all workflows |
| POST | `/commissioning/test` | Test device |
| POST | `/commissioning/cancel/{workflow_id}` | Cancel workflow |
| GET | `/commissioning/providers` | List supported providers |
| GET | `/commissioning/capabilities` | List supported capabilities |
| POST | `/commissioning/cleanup` | Clean up workflows |

### Capability Control Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/capability/{provider}/{device_id}/switch/on` | Turn device on |
| POST | `/capability/{provider}/{device_id}/switch/off` | Turn device off |
| POST | `/capability/{provider}/{device_id}/dimmer/set` | Set brightness |
| POST | `/capability/{provider}/{device_id}/color/hsv` | Set HSV color |
| POST | `/capability/{provider}/{device_id}/color/temp` | Set color temperature |

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Hue Bridge Configuration (optional - can be discovered automatically)
HUE_BRIDGE_IP=192.168.1.100
HUE_BRIDGE_USERNAME=your_username
HUE_BRIDGE_CLIENT_KEY=your_client_key

# API Configuration
API_TOKEN=your-api-key
```

### Bridge Configuration

Bridges are automatically discovered and configured. Manual configuration is also supported:

```python
from iot_api_discovery.tools.hue.adapters import HueBridgeManager

bridge_manager = HueBridgeManager()
bridge_manager.add_bridge(
    bridge_id="hue_bridge_1",
    ip_address="192.168.1.100",
    username="abc123def456",
    client_key="optional_client_key"
)
```

## Device Capabilities

### Supported Capabilities

1. **Switchable**
   - Turn on/off
   - Get current state

2. **Dimmable**
   - Set brightness (0-100%)
   - Inherits from Switchable

3. **Color Control**
   - Set HSV color (hue: 0-360°, saturation: 0-1, value: 0-1)
   - Set color temperature (153-500 mireds)
   - Inherits from Dimmable

### Device Types

- **Extended color light**: Full color control
- **Color temperature light**: White temperature control
- **Dimmable light**: Brightness control only
- **On/Off light**: Basic switch control

## Error Handling

### Common Errors

1. **Bridge Not Found**
   ```json
   {
     "ok": false,
     "error": "Bridge not found in discovery results",
     "message": "Discovery failed"
   }
   ```

2. **Pairing Failed**
   ```json
   {
     "ok": false,
     "error": "link button not pressed",
     "message": "Press the link button on the bridge and try again"
   }
   ```

3. **Device Not Found**
   ```json
   {
     "ok": false,
     "error": "Device not found",
     "reachable": false
   }
   ```

### Troubleshooting

1. **Bridge Discovery Issues**
   - Ensure bridge is powered on and connected to network
   - Check network connectivity
   - Try manual IP address specification

2. **Pairing Issues**
   - Press the link button on the bridge within 30 seconds
   - Ensure bridge is not already paired with maximum apps
   - Check network connectivity

3. **Device Control Issues**
   - Verify device is powered on
   - Check bridge connectivity
   - Verify device capabilities

## Security Considerations

1. **Authentication**
   - All API endpoints require API key authentication
   - Bridge pairing uses secure token exchange

2. **Network Security**
   - Bridge communication uses HTTP (consider HTTPS for production)
   - Local network access required

3. **Token Management**
   - Bridge tokens are stored securely
   - Tokens can be revoked by resetting bridge

## Performance Considerations

1. **Discovery**
   - Cloud discovery: ~2-5 seconds
   - Network scanning: ~10-30 seconds (depending on network size)

2. **Pairing**
   - Bridge pairing: ~5-10 seconds
   - Requires user interaction (link button)

3. **Device Control**
   - Command execution: ~100-500ms
   - State retrieval: ~100-300ms

## Future Enhancements

1. **Enhanced Discovery**
   - mDNS/Bonjour discovery
   - UPnP discovery
   - Bluetooth discovery

2. **Advanced Features**
   - Scene management
   - Group control
   - Schedule management
   - Motion sensor integration

3. **Security Improvements**
   - HTTPS support
   - Certificate-based authentication
   - Token encryption

4. **Performance Optimizations**
   - Connection pooling
   - Caching
   - Batch operations

## Integration Examples

### Python Client

```python
import httpx

async def control_hue_light():
    async with httpx.AsyncClient() as client:
        # Turn on light
        response = await client.post(
            "http://localhost:8000/capability/hue/hue_192_168_1_100:1/switch/on",
            headers={"X-API-Key": "your-api-key"}
        )
        
        # Set color
        response = await client.post(
            "http://localhost:8000/capability/hue/hue_192_168_1_100:1/color/hsv",
            headers={"X-API-Key": "your-api-key", "Content-Type": "application/json"},
            json={"h": 120, "s": 1.0, "v": 0.8}
        )
```

### JavaScript Client

```javascript
async function controlHueLight() {
    // Turn on light
    await fetch('http://localhost:8000/capability/hue/hue_192_168_1_100:1/switch/on', {
        method: 'POST',
        headers: {
            'X-API-Key': 'your-api-key'
        }
    });
    
    // Set color
    await fetch('http://localhost:8000/capability/hue/hue_192_168_1_100:1/color/hsv', {
        method: 'POST',
        headers: {
            'X-API-Key': 'your-api-key',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            h: 120,
            s: 1.0,
            v: 0.8
        })
    });
}
```

## Conclusion

The Philips Hue integration provides a comprehensive solution for discovering, commissioning, and controlling Hue devices. The modular architecture allows for easy extension to other providers while maintaining a consistent API interface.

For more information, see the individual component documentation and API reference.
