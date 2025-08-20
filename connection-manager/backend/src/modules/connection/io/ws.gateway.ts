import { Injectable, OnModuleInit } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';

@Injectable()
export class WsGateway implements OnModuleInit {
  constructor(private readonly bus: EventBus) {}

  onModuleInit(): void {
    // Placeholder: In a real implementation use @WebSocketGateway
    this.bus.on('conn.shadow.updated', () => {});
  }
}

