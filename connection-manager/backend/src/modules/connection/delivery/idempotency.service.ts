import { Injectable } from '@nestjs/common';

@Injectable()
export class IdempotencyService {
  private seen = new Set<string>();

  key(deviceId: string, idempotencyKey: string): string {
    return `${deviceId}:${idempotencyKey}`;
  }

  checkAndRecord(deviceId: string, idempotencyKey: string): boolean {
    const k = this.key(deviceId, idempotencyKey);
    if (this.seen.has(k)) return false;
    this.seen.add(k);
    return true;
  }
}

