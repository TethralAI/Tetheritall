export declare class IdempotencyService {
    private seen;
    key(deviceId: string, idempotencyKey: string): string;
    checkAndRecord(deviceId: string, idempotencyKey: string): boolean;
}
