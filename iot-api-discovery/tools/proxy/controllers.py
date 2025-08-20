from __future__ import annotations

from typing import Any, Dict, List, Optional


def known_proxy_controllers() -> List[Dict[str, Any]]:
    """List proxy controllers that smartphones can talk to natively (HTTP/MQTT/WS).

    Examples include: Philips Hue Bridge (Zigbee), deCONZ/ConBee (Zigbee REST API),
    Home Assistant, Z-Wave JS Server (Z-Wave), Zigbee2MQTT (MQTT), Tuya gateways, etc.
    """
    return [
        {"name": "Philips Hue Bridge", "protocol": "zigbee", "transport": "http", "probe": "hue_http"},
        {"name": "deCONZ REST API", "protocol": "zigbee", "transport": "http", "probe": "deconz_http"},
        {"name": "Zigbee2MQTT", "protocol": "zigbee", "transport": "mqtt", "probe": "zigbee2mqtt"},
        {"name": "Z-Wave JS", "protocol": "zwave", "transport": "ws/http", "probe": "zwave_js"},
        {"name": "Home Assistant", "protocol": "multi", "transport": "http/ws/mqtt", "probe": "home_assistant"},
    ]

