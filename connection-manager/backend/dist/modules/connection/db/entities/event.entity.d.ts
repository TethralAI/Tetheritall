export declare class EventEntity {
    id: string;
    deviceId: string;
    capability: string;
    dataClass: 'telemetry' | 'state' | 'diagnostic' | 'identifier' | 'location';
    purpose: 'automation' | 'troubleshooting' | 'analytics';
    value: unknown;
    seq: number;
    policyVersion: string;
    ts: Date;
}
