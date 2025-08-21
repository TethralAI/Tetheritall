export declare class SecurityQuarantineEntity {
    id: string;
    deviceId: string;
    mode: 'read_only' | 'block';
    ttlSec: number | null;
    appliedAt: Date;
    updatedAt: Date;
}
