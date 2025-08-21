import { Injectable } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';

export interface HeartbeatSample {
  deviceId: string;
  ts: number;
  rttMs?: number;
  packetLossPct?: number;
}

@Injectable()
export class HealthMonitor {
  private lastBeat = new Map<string, HeartbeatSample>();

  constructor(private readonly bus: EventBus) {}

  recordHeartbeat(sample: HeartbeatSample): void {
    const prev = this.lastBeat.get(sample.deviceId);
    this.lastBeat.set(sample.deviceId, sample);
    const now = Date.now();
    if (prev) {
      const gap = now - prev.ts;
      if (gap > 2 * 60_000 || (sample.packetLossPct ?? 0) > 50) {
        this.bus.emit({ type: 'sec.signal.breakdown', deviceId: sample.deviceId, detail: { gap, sample } });
      }
    }
  }
}

