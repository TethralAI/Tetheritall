export type InternalEvent = {
    type: 'conn.device.connected' | 'conn.device.disconnected' | 'conn.device.degraded';
    deviceId: string;
} | {
    type: 'conn.command.accepted' | 'conn.command.delivering' | 'conn.command.applied' | 'conn.command.failed' | 'conn.command.expired';
    deviceId: string;
    commandId: string;
} | {
    type: 'conn.shadow.updated';
    deviceId: string;
    version: number;
    shadow: unknown;
} | {
    type: 'conn.privacy.allowed' | 'conn.privacy.blocked';
    deviceId: string;
    policyVersion: string;
    reason?: string;
} | {
    type: 'sec.signal.breakdown' | 'sec.signal.anomaly_local' | 'sec.signal.intrusion_suspected';
    deviceId: string;
    detail?: unknown;
} | {
    type: 'sec.action.quarantine_applied' | 'sec.action.quarantine_released';
    deviceId: string;
    mode: 'read_only' | 'block';
};
export declare class EventBus {
    private emitter;
    emit(event: InternalEvent): void;
    on<T extends InternalEvent['type']>(type: T, handler: (e: Extract<InternalEvent, {
        type: T;
    }>) => void): void;
}
