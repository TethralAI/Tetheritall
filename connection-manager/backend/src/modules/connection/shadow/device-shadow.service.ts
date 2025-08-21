import { Inject, Injectable } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';
import { SHADOW_STORE } from '../db/store.tokens.js';
import type { ShadowStore } from '../db/shadow.store.js';

export interface ShadowEntry {
  version: number;
  reported: Record<string, unknown>;
  updatedAt: number;
}

@Injectable()
export class DeviceShadowService {
  constructor(private readonly bus: EventBus, @Inject(SHADOW_STORE) private readonly store: ShadowStore) {}

  get(deviceId: string): Promise<ShadowEntry | undefined> {
    return this.store.get(deviceId);
  }

  async applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry> {
    const next = await this.store.applyUpdate(deviceId, version, patch);
    this.bus.emit({ type: 'conn.shadow.updated', deviceId, version: version, shadow: next });
    return next;
  }
}

