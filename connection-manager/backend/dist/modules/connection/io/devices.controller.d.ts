import { DeviceShadowService } from '../shadow/device-shadow.service.js';
import type { DeviceStore } from '../db/device.store.js';
type CreateDeviceDto = {
    deviceId: string;
    capabilities?: string[];
    status?: 'online' | 'offline';
};
export declare class DevicesController {
    private readonly shadow;
    private readonly devices;
    constructor(shadow: DeviceShadowService, devices: DeviceStore);
    create(body: CreateDeviceDto): Promise<import("../db/device.store.js").DeviceRecord>;
    list(capability?: string, status?: string): Promise<{
        items: import("../db/device.store.js").DeviceRecord[];
    }>;
    shadowGet(id: string): Promise<import("../shadow/device-shadow.service.js").ShadowEntry>;
    shadowUpdate(id: string, body: {
        version: number;
        patch: Record<string, unknown>;
    }): Promise<import("../shadow/device-shadow.service.js").ShadowEntry>;
}
export {};
