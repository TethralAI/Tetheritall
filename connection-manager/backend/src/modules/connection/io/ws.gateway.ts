import { OnModuleInit } from '@nestjs/common';
import { WebSocketGateway, WebSocketServer, SubscribeMessage, MessageBody, ConnectedSocket } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { EventBus, InternalEvent } from '../observe/event-bus.js';

type StreamSubscribe = { deviceId?: string; capability?: string; room?: string };

@WebSocketGateway({ namespace: '/v1/stream', cors: { origin: true } })
export class WsGateway implements OnModuleInit {
  @WebSocketServer()
  server!: Server;

  constructor(private readonly bus: EventBus) {}

  onModuleInit(): void {
    const forward = (event: InternalEvent): void => {
      const payload = event as any;
      const deviceId = (payload.deviceId ?? payload.device_id) as string | undefined;
      if (deviceId) this.server.to(`device:${deviceId}`).emit(event.type, payload);
      const capability = (payload.capability as string | undefined) ?? (payload.shadow?.capability as string | undefined);
      if (capability) this.server.to(`cap:${capability}`).emit(event.type, payload);
      const room = (payload.room as string | undefined) ?? (payload.location as string | undefined);
      if (room) this.server.to(`room:${room}`).emit(event.type, payload);
      this.server.emit(event.type, payload);
    };
    this.bus.on('conn.shadow.updated', forward as any);
    this.bus.on('conn.command.accepted', forward as any);
    this.bus.on('conn.command.delivering', forward as any);
    this.bus.on('conn.command.applied', forward as any);
    this.bus.on('conn.command.failed', forward as any);
    this.bus.on('conn.privacy.allowed', forward as any);
    this.bus.on('conn.privacy.blocked', forward as any);
    this.bus.on('sec.signal.breakdown', forward as any);
    this.bus.on('sec.signal.anomaly_local', forward as any);
    this.bus.on('sec.signal.intrusion_suspected', forward as any);
  }

  @SubscribeMessage('subscribe')
  subscribe(@MessageBody() body: StreamSubscribe, @ConnectedSocket() client: Socket) {
    if (body.deviceId) client.join(`device:${body.deviceId}`);
    if (body.capability) client.join(`cap:${body.capability}`);
    if (body.room) client.join(`room:${body.room}`);
    return { ok: true };
  }
}

