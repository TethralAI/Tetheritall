import { EventBus } from '../observe/event-bus.js';
export interface ShadowEntry {
    version: number;
    reported: Record<string, unknown>;
    updatedAt: number;
}
export declare class DeviceShadowService {
    private readonly bus;
    private shadows;
    constructor(bus: EventBus);
    get(deviceId: string): ShadowEntry | undefined;
    applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): ShadowEntry;
}
