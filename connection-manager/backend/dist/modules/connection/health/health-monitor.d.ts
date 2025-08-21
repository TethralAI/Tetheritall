import { EventBus } from '../observe/event-bus.js';
export interface HeartbeatSample {
    deviceId: string;
    ts: number;
    rttMs?: number;
    packetLossPct?: number;
}
export declare class HealthMonitor {
    private readonly bus;
    private lastBeat;
    constructor(bus: EventBus);
    recordHeartbeat(sample: HeartbeatSample): void;
}
