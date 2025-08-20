import { Module } from '@nestjs/common';
import { PrivacyModule } from './privacy/privacy.module.js';
import { IoModule } from './io/io.module.js';
import { ShadowModule } from './shadow/shadow.module.js';
import { DeliveryModule } from './delivery/delivery.module.js';
import { ObserveModule } from './observe/observe.module.js';

@Module({
  imports: [PrivacyModule, IoModule, ShadowModule, DeliveryModule, ObserveModule],
})
export class ConnectionModule {}

