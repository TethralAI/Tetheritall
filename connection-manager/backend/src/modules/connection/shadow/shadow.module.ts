import { Module } from '@nestjs/common';
import { DeviceShadowService } from './device-shadow.service.js';
import { ObserveModule } from '../observe/observe.module.js';
import { DbModule } from '../db/db.module.js';

@Module({ imports: [ObserveModule, DbModule], providers: [DeviceShadowService], exports: [DeviceShadowService] })
export class ShadowModule {}

