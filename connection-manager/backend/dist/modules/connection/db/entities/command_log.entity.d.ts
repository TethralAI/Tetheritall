export declare class CommandLogEntity {
    id: string;
    deviceId: string;
    capability: string;
    params: unknown;
    priority: 'emergency' | 'routine' | 'background';
    deadline: number | null;
    idempotencyKey: string;
    status: 'accepted' | 'delivering' | 'applied' | 'failed' | 'expired';
    error: string | null;
    createdAt: Date;
    updatedAt: Date;
}
