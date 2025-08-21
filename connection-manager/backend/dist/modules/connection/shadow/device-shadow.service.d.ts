import { EventBus } from '../observe/event-bus.js';
import type { ShadowStore } from '../db/shadow.store.js';
export interface ShadowEntry {
    version: number;
    reported: Record<string, unknown>;
    updatedAt: number;
}
export declare class DeviceShadowService {
    private readonly bus;
    private readonly store;
    constructor(bus: EventBus, store: ShadowStore);
    get(deviceId: string): Promise<ShadowEntry | undefined>;
    applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry>;
}
