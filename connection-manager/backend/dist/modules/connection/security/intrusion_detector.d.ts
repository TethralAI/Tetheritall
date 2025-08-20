import { EventBus } from '../observe/event-bus.js';
export type IntrusionSignal = {
    type: 'sequence_regression';
    deviceId: string;
    seq: number;
    lastSeq: number;
} | {
    type: 'capability_mutation';
    deviceId: string;
    capability: string;
} | {
    type: 'forbidden_source';
    deviceId: string;
    source: string;
} | {
    type: 'command_effect_mismatch';
    deviceId: string;
    commandId: string;
} | {
    type: 'replay';
    deviceId: string;
    seq: number;
};
export declare class IntrusionDetector {
    private readonly bus;
    private lastSeq;
    constructor(bus: EventBus);
    onSequence(deviceId: string, seq: number): void;
}
