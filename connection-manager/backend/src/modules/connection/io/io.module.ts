import { Module } from '@nestjs/common';
import { IngestController } from './ingest.controller.js';
import { PrivacyModule } from '../privacy/privacy.module.js';
import { EventBus } from '../observe/event-bus.js';
import { WsGateway } from './ws.gateway.js';

@Module({
  imports: [PrivacyModule],
  controllers: [IngestController],
  providers: [EventBus, WsGateway],
  exports: [EventBus],
})
export class IoModule {}

