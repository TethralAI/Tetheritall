import { OnModuleInit } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';
export declare class WsGateway implements OnModuleInit {
    private readonly bus;
    constructor(bus: EventBus);
    onModuleInit(): void;
}
