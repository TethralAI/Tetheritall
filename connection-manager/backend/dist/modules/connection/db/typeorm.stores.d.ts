import { Repository } from 'typeorm';
import { DeviceEntity } from './entities/device.entity.js';
import { DeviceShadowEntity } from './entities/device_shadow.entity.js';
import type { DeviceRecord, DeviceStore } from './device.store.js';
import type { ShadowEntry, ShadowStore } from './shadow.store.js';
export declare class OrmDeviceStore implements DeviceStore {
    private readonly repo;
    constructor(repo: Repository<DeviceEntity>);
    create(deviceId: string, capabilities: string[], status: 'online' | 'offline'): Promise<DeviceRecord>;
    list(filter?: {
        capability?: string;
        status?: 'online' | 'offline';
    }): Promise<DeviceRecord[]>;
}
export declare class OrmShadowStore implements ShadowStore {
    private readonly repo;
    constructor(repo: Repository<DeviceShadowEntity>);
    get(deviceId: string): Promise<ShadowEntry | undefined>;
    applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry>;
}
