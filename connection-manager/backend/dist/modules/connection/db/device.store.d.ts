export interface DeviceRecord {
    id: string;
    capabilities: string[];
    status: 'online' | 'offline';
    createdAt: number;
}
export interface DeviceStore {
    create(deviceId: string, capabilities: string[], status: 'online' | 'offline'): Promise<DeviceRecord>;
    list(filter?: {
        capability?: string;
        status?: 'online' | 'offline';
    }): Promise<DeviceRecord[]>;
}
