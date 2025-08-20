import { PriorityQueueService, Priority } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';
declare class CommandDto {
    capability: string;
    params: unknown;
    priority: Priority;
    idempotencyKey: string;
    deadline?: number;
}
export declare class CommandController {
    private readonly pq;
    private readonly idem;
    constructor(pq: PriorityQueueService, idem: IdempotencyService);
    enqueue(body: CommandDto): Promise<{
        commandId: string;
    }>;
}
export {};
