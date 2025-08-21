import { OnModuleInit } from '@nestjs/common';
import { WsResponse } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { EventBus } from '../observe/event-bus.js';
type StreamSubscribe = {
    deviceId?: string;
    capability?: string;
    room?: string;
};
export declare class WsGateway implements OnModuleInit {
    private readonly bus;
    server: Server;
    constructor(bus: EventBus);
    onModuleInit(): void;
    subscribe(body: StreamSubscribe, client: Socket): WsResponse<{
        ok: true;
    }> | {
        ok: true;
    };
}
export {};
