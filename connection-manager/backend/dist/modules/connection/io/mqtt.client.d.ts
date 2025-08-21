import { OnModuleInit } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';
export declare class MqttService implements OnModuleInit {
    private readonly bus;
    private readonly logger;
    private client;
    constructor(bus: EventBus);
    onModuleInit(): void;
}
