import { DeviceRecord, DeviceStore } from './device.store.js';
import { ShadowEntry, ShadowStore } from './shadow.store.js';
export declare class InMemoryDeviceStore implements DeviceStore {
    private devices;
    create(deviceId: string, capabilities: string[], status: 'online' | 'offline'): Promise<DeviceRecord>;
    list(filter?: {
        capability?: string;
        status?: 'online' | 'offline';
    }): Promise<DeviceRecord[]>;
}
export declare class InMemoryShadowStore implements ShadowStore {
    private shadows;
    get(deviceId: string): Promise<ShadowEntry | undefined>;
    applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry>;
}
