import { OnModuleInit } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { EventBus } from '../observe/event-bus.js';
export declare class CommandWorker implements OnModuleInit {
    private readonly pq;
    private readonly bus;
    private readonly logger;
    private running;
    constructor(pq: PriorityQueueService, bus: EventBus);
    start(): void;
    stop(): void;
    private loop;
    onModuleInit(): void;
}
