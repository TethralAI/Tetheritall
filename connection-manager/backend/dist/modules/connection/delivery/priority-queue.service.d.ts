export type Priority = 'emergency' | 'routine' | 'background';
export interface EnqueuedCommand {
    commandId: string;
    deviceId: string;
    capability: string;
    params: unknown;
    priority: Priority;
    deadline?: number;
    idempotencyKey: string;
    enqueuedAt: number;
}
export declare class PriorityQueueService {
    private queues;
    enqueue(cmd: EnqueuedCommand): void;
    dequeue(): EnqueuedCommand | undefined;
    size(): number;
}
