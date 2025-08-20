import { EventBus } from '../observe/event-bus.js';
export type QuarantineMode = 'read_only' | 'block';
export declare class QuarantineService {
    private readonly bus;
    private devices;
    constructor(bus: EventBus);
    apply(deviceId: string, mode: QuarantineMode): void;
    release(deviceId: string): void;
    isBlocked(deviceId: string): boolean;
}
