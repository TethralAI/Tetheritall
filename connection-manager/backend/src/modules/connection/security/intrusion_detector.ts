import { Injectable } from '@nestjs/common';
import { EventBus } from '../observe/event-bus.js';

export type IntrusionSignal =
  | { type: 'sequence_regression'; deviceId: string; seq: number; lastSeq: number }
  | { type: 'capability_mutation'; deviceId: string; capability: string }
  | { type: 'forbidden_source'; deviceId: string; source: string }
  | { type: 'command_effect_mismatch'; deviceId: string; commandId: string }
  | { type: 'replay'; deviceId: string; seq: number };

@Injectable()
export class IntrusionDetector {
  private lastSeq = new Map<string, number>();

  constructor(private readonly bus: EventBus) {}

  onSequence(deviceId: string, seq: number): void {
    const last = this.lastSeq.get(deviceId) ?? -1;
    if (seq <= last) {
      this.bus.emit({ type: 'sec.signal.intrusion_suspected', deviceId, detail: { reason: 'sequence_regression', seq, last } });
    }
    this.lastSeq.set(deviceId, seq);
  }
}

