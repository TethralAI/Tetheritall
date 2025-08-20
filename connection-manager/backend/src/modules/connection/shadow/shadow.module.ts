import { Module } from '@nestjs/common';
import { DeviceShadowService } from './device-shadow.service.js';
import { ObserveModule } from '../observe/observe.module.js';

@Module({ imports: [ObserveModule], providers: [DeviceShadowService], exports: [DeviceShadowService] })
export class ShadowModule {}

