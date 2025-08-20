import { Injectable } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';

export type QuarantineMode = 'read_only' | 'block';

@Injectable()
export class QuarantineService {
  private devices = new Map<string, { mode: QuarantineMode; appliedAt: number }>();

  constructor(private readonly bus: EventBus) {}

  apply(deviceId: string, mode: QuarantineMode): void {
    this.devices.set(deviceId, { mode, appliedAt: Date.now() });
    this.bus.emit({ type: 'sec.action.quarantine_applied', deviceId, mode });
  }

  release(deviceId: string): void {
    const existing = this.devices.get(deviceId);
    if (!existing) return;
    this.devices.delete(deviceId);
    this.bus.emit({ type: 'sec.action.quarantine_released', deviceId, mode: existing.mode });
  }

  isBlocked(deviceId: string): boolean {
    const q = this.devices.get(deviceId);
    return !!q && q.mode === 'block';
  }
}

