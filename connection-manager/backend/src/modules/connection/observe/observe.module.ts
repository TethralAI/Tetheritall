import { Module } from '@nestjs/common';
import { EventBus } from './event-bus.js';

@Module({ providers: [EventBus], exports: [EventBus] })
export class ObserveModule {}

