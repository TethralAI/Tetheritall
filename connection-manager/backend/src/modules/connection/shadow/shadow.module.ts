import { Module } from '@nestjs/common';
import { DeviceShadowService } from './device-shadow.service.js';

@Module({ providers: [DeviceShadowService], exports: [DeviceShadowService] })
export class ShadowModule {}

