import { Module } from '@nestjs/common';
import { IngestController } from './ingest.controller.js';
import { PrivacyModule } from '../privacy/privacy.module.js';
import { EventBus } from '../observe/event-bus.js';
import { WsGateway } from './ws.gateway.js';
import { CommissioningController } from './commissioning.controller.js';
import { DevicesController } from './devices.controller.js';
import { ShadowModule } from '../shadow/shadow.module.js';

@Module({
  imports: [PrivacyModule, ShadowModule],
  controllers: [IngestController, CommissioningController, DevicesController],
  providers: [EventBus, WsGateway],
  exports: [EventBus],
})
export class IoModule {}

