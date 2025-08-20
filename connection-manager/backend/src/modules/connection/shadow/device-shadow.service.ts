import { Injectable } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';

export interface ShadowEntry {
  version: number;
  reported: Record<string, unknown>;
  updatedAt: number;
}

@Injectable()
export class DeviceShadowService {
  private shadows = new Map<string, ShadowEntry>();
  constructor(private readonly bus: EventBus) {}

  get(deviceId: string): ShadowEntry | undefined {
    return this.shadows.get(deviceId);
  }

  // Merge with versioning, simple last-write-wins if version higher; allow small re-order window by idempotent apply
  applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): ShadowEntry {
    const current = this.shadows.get(deviceId) ?? { version: 0, reported: {}, updatedAt: 0 };
    if (version <= current.version) return current;
    const next: ShadowEntry = {
      version,
      reported: { ...current.reported, ...patch },
      updatedAt: Date.now(),
    };
    this.shadows.set(deviceId, next);
    this.bus.emit({ type: 'conn.shadow.updated', deviceId, version: version, shadow: next });
    return next;
  }
}

