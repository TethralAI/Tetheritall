var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { WebSocketGateway, WebSocketServer, SubscribeMessage, MessageBody, ConnectedSocket } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { EventBus } from '../observe/event-bus.js';
import { UseGuards } from '@nestjs/common';
import { WsJwtGuard } from './ws.auth.js';
let WsGateway = class WsGateway {
    bus;
    server;
    constructor(bus) {
        this.bus = bus;
    }
    onModuleInit() {
        const forward = (event) => {
            const payload = event;
            const deviceId = (payload.deviceId ?? payload.device_id);
            if (deviceId)
                this.server.to(`device:${deviceId}`).emit(event.type, payload);
            const capability = payload.capability ?? payload.shadow?.capability;
            if (capability)
                this.server.to(`cap:${capability}`).emit(event.type, payload);
            const room = payload.room ?? payload.location;
            if (room)
                this.server.to(`room:${room}`).emit(event.type, payload);
            this.server.emit(event.type, payload);
        };
        this.bus.on('conn.shadow.updated', forward);
        this.bus.on('conn.command.accepted', forward);
        this.bus.on('conn.command.delivering', forward);
        this.bus.on('conn.command.applied', forward);
        this.bus.on('conn.command.failed', forward);
        this.bus.on('conn.privacy.allowed', forward);
        this.bus.on('conn.privacy.blocked', forward);
        this.bus.on('sec.signal.breakdown', forward);
        this.bus.on('sec.signal.anomaly_local', forward);
        this.bus.on('sec.signal.intrusion_suspected', forward);
    }
    subscribe(body, client) {
        if (body.deviceId)
            client.join(`device:${body.deviceId}`);
        if (body.capability)
            client.join(`cap:${body.capability}`);
        if (body.room)
            client.join(`room:${body.room}`);
        return { ok: true };
    }
};
__decorate([
    WebSocketServer(),
    __metadata("design:type", Server)
], WsGateway.prototype, "server", void 0);
__decorate([
    SubscribeMessage('subscribe'),
    __param(0, MessageBody()),
    __param(1, ConnectedSocket()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Socket]),
    __metadata("design:returntype", Object)
], WsGateway.prototype, "subscribe", null);
WsGateway = __decorate([
    WebSocketGateway({ namespace: '/v1/stream', cors: { origin: true } }),
    UseGuards(WsJwtGuard),
    __metadata("design:paramtypes", [EventBus])
], WsGateway);
export { WsGateway };
//# sourceMappingURL=ws.gateway.js.map