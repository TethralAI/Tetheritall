export interface ShadowEntry {
    version: number;
    reported: Record<string, unknown>;
    updatedAt: number;
}
export declare class DeviceShadowService {
    private shadows;
    get(deviceId: string): ShadowEntry | undefined;
    applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): ShadowEntry;
}
