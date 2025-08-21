import { Body, Controller, Get, Inject, Param, Post, Query } from '@nestjs/common';
import { DeviceShadowService } from '../shadow/device-shadow.service.js';
import { DEVICE_STORE } from '../db/store.tokens.js';
import type { DeviceStore } from '../db/device.store.js';

type CreateDeviceDto = { deviceId: string; capabilities?: string[]; status?: 'online' | 'offline' };

@Controller('/v1/devices')
export class DevicesController {
  constructor(private readonly shadow: DeviceShadowService, @Inject(DEVICE_STORE) private readonly devices: DeviceStore) {}

  @Post('')
  create(@Body() body: CreateDeviceDto) {
    const id = body.deviceId;
    return this.devices.create(id, body.capabilities ?? [], body.status ?? 'offline');
  }

  @Get('')
  list(@Query('capability') capability?: string, @Query('status') status?: string) {
    return this.devices.list({ capability: capability ?? undefined, status: (status as any) ?? undefined }).then((items) => ({ items }));
  }

  @Get('/:id/shadow')
  shadowGet(@Param('id') id: string) {
    return this.shadow.get(id).then((s) => s ?? { version: 0, reported: {}, updatedAt: 0 });
  }

  @Post('/:id/shadow')
  async shadowUpdate(@Param('id') id: string, @Body() body: { version: number; patch: Record<string, unknown> }) {
    const next = await this.shadow.applyUpdate(id, body.version, body.patch);
    return next;
  }
}

