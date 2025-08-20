import { DeviceShadowService } from '../shadow/device-shadow.service.js';
type CreateDeviceDto = {
    deviceId: string;
    capabilities?: string[];
    status?: 'online' | 'offline';
};
export declare class DevicesController {
    private readonly shadow;
    private devices;
    constructor(shadow: DeviceShadowService);
    create(body: CreateDeviceDto): {
        id: string;
    };
    list(capability?: string, status?: string): {
        items: {
            id: string;
            capabilities: string[];
            status: "online" | "offline";
        }[];
    };
    shadowGet(id: string): import("../shadow/device-shadow.service.js").ShadowEntry;
}
export {};
