from __future__ import annotations

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import logging

from tools.hue.commissioning import HueCommissioningService
from api.server import rate_limiter, require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hue", tags=["Philips Hue Commissioning"])

# Initialize commissioning service
commissioning_service = HueCommissioningService()


class BridgeDiscoveryRequest(BaseModel):
    network_range: Optional[str] = None


class BridgePairingRequest(BaseModel):
    bridge_ip: str
    app_name: str = "iot-orchestrator"
    device_name: str = "server"


class DeviceCommissioningRequest(BaseModel):
    device_id: str
    name: Optional[str] = None
    room: Optional[str] = None
    zone: Optional[str] = None


class DeviceTestRequest(BaseModel):
    device_id: str


@router.post("/discover-bridges", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def discover_hue_bridges(request: BridgeDiscoveryRequest) -> Dict[str, Any]:
    """Discover Philips Hue bridges on the network."""
    try:
        bridges = await commissioning_service.discover_hue_bridges(request.network_range)
        
        return {
            "ok": True,
            "bridges": bridges,
            "count": len(bridges),
            "message": f"Discovered {len(bridges)} Hue bridge(s)"
        }
        
    except Exception as e:
        logger.error(f"Error discovering Hue bridges: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.post("/pair-bridge", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def pair_hue_bridge(request: BridgePairingRequest) -> Dict[str, Any]:
    """Pair with a Philips Hue bridge."""
    try:
        result = await commissioning_service.pair_bridge(
            request.bridge_ip,
            request.app_name,
            request.device_name
        )
        
        if result.get('ok'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Pairing failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pairing with Hue bridge: {e}")
        raise HTTPException(status_code=500, detail=f"Pairing failed: {str(e)}")


@router.get("/bridges", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def list_paired_bridges() -> Dict[str, Any]:
    """List all paired Philips Hue bridges."""
    try:
        status = await commissioning_service.get_commissioning_status()
        
        return {
            "ok": True,
            "bridges": status['bridges'],
            "total_bridges": status['total_bridges'],
            "message": f"Found {status['total_bridges']} paired bridge(s)"
        }
        
    except Exception as e:
        logger.error(f"Error listing paired bridges: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list bridges: {str(e)}")


@router.get("/bridges/{bridge_id}/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def discover_bridge_devices(bridge_id: str) -> Dict[str, Any]:
    """Discover devices on a specific Philips Hue bridge."""
    try:
        devices = await commissioning_service.discover_devices(bridge_id)
        
        return {
            "ok": True,
            "bridge_id": bridge_id,
            "devices": devices,
            "count": len(devices),
            "message": f"Discovered {len(devices)} device(s) on bridge {bridge_id}"
        }
        
    except Exception as e:
        logger.error(f"Error discovering devices on bridge {bridge_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Device discovery failed: {str(e)}")


@router.post("/devices/test", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def test_device_communication(request: DeviceTestRequest) -> Dict[str, Any]:
    """Test communication with a specific device."""
    try:
        result = await commissioning_service.test_device_communication(request.device_id)
        
        if result.get('ok'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Communication test failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing device communication: {e}")
        raise HTTPException(status_code=500, detail=f"Communication test failed: {str(e)}")


@router.post("/devices/commission", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def commission_device(request: DeviceCommissioningRequest) -> Dict[str, Any]:
    """Commission a specific device."""
    try:
        device_config = {}
        if request.name:
            device_config['name'] = request.name
        if request.room:
            device_config['room'] = request.room
        if request.zone:
            device_config['zone'] = request.zone
        
        result = await commissioning_service.commission_device(request.device_id, device_config)
        
        if result.get('ok'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Commissioning failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error commissioning device: {e}")
        raise HTTPException(status_code=500, detail=f"Commissioning failed: {str(e)}")


@router.get("/status", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def get_commissioning_status() -> Dict[str, Any]:
    """Get comprehensive commissioning status."""
    try:
        status = await commissioning_service.get_commissioning_status()
        
        return {
            "ok": True,
            "status": status,
            "message": f"Commissioning status: {status['total_bridges']} bridges, {status['total_devices']} devices"
        }
        
    except Exception as e:
        logger.error(f"Error getting commissioning status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.delete("/bridges/{bridge_id}", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def remove_bridge(bridge_id: str) -> Dict[str, Any]:
    """Remove a paired Philips Hue bridge."""
    try:
        result = await commissioning_service.remove_bridge(bridge_id)
        
        if result.get('ok'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Bridge removal failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bridge: {e}")
        raise HTTPException(status_code=500, detail=f"Bridge removal failed: {str(e)}")


@router.post("/bridges/{bridge_id}/refresh", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def refresh_bridge_devices(bridge_id: str) -> Dict[str, Any]:
    """Refresh device list for a specific bridge."""
    try:
        devices = await commissioning_service.discover_devices(bridge_id)
        
        return {
            "ok": True,
            "bridge_id": bridge_id,
            "devices": devices,
            "count": len(devices),
            "message": f"Refreshed {len(devices)} device(s) on bridge {bridge_id}"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing bridge devices: {e}")
        raise HTTPException(status_code=500, detail=f"Device refresh failed: {str(e)}")


@router.get("/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def list_all_devices() -> Dict[str, Any]:
    """List all devices across all bridges."""
    try:
        status = await commissioning_service.get_commissioning_status()
        
        all_devices = []
        for bridge_id, devices in status['devices'].items():
            for device in devices:
                device['bridge_id'] = bridge_id
                all_devices.append(device)
        
        return {
            "ok": True,
            "devices": all_devices,
            "total_devices": len(all_devices),
            "total_bridges": status['total_bridges'],
            "message": f"Found {len(all_devices)} device(s) across {status['total_bridges']} bridge(s)"
        }
        
    except Exception as e:
        logger.error(f"Error listing all devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


@router.get("/devices/{device_id}", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
async def get_device_info(device_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific device."""
    try:
        # Test communication to get current state
        test_result = await commissioning_service.test_device_communication(device_id)
        
        if not test_result.get('ok'):
            raise HTTPException(status_code=404, detail="Device not found or not reachable")
        
        # Get device info from bridge
        bridge_id = device_id.split(':', 1)[0] if ':' in device_id else None
        if bridge_id:
            devices = await commissioning_service.discover_devices(bridge_id)
            device_info = next((d for d in devices if d['device_id'] == device_id), None)
            
            if device_info:
                device_info['current_state'] = test_result.get('state', {})
                return {
                    "ok": True,
                    "device": device_info
                }
        
        raise HTTPException(status_code=404, detail="Device not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device info: {str(e)}")
