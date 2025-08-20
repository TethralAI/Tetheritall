import { Body, Controller, Get, Param, Post, Query } from '@nestjs/common';
import { DeviceShadowService } from '../shadow/device-shadow.service.js';

type CreateDeviceDto = { deviceId: string; capabilities?: string[]; status?: 'online' | 'offline' };

@Controller('/v1/devices')
export class DevicesController {
  private devices = new Map<string, { id: string; capabilities: string[]; status: 'online' | 'offline' }>();

  constructor(private readonly shadow: DeviceShadowService) {}

  @Post('')
  create(@Body() body: CreateDeviceDto) {
    const id = body.deviceId;
    this.devices.set(id, { id, capabilities: body.capabilities ?? [], status: body.status ?? 'offline' });
    return { id };
  }

  @Get('')
  list(@Query('capability') capability?: string, @Query('status') status?: string) {
    const items = Array.from(this.devices.values()).filter((d) => {
      if (capability && !d.capabilities.includes(capability)) return false;
      if (status && d.status !== status) return false;
      return true;
    });
    return { items };
  }

  @Get('/:id/shadow')
  shadowGet(@Param('id') id: string) {
    const s = this.shadow.get(id);
    return s ?? { version: 0, reported: {}, updatedAt: 0 };
  }
}

