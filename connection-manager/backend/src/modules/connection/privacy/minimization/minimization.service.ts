import { Injectable } from '@nestjs/common';

export interface MinimizationOptions {
  roundTimestampMs?: number; // e.g., 1000 -> round to nearest second
  numericBucket?: number; // e.g., 0.5 -> bucket temps to 0.5
  stripIdentifiers?: boolean;
  truncatePayloadBytes?: number; // max bytes for JSON stringified value
}

@Injectable()
export class MinimizationService {
  apply<T = unknown>(value: T, opts: MinimizationOptions): unknown {
    let v: unknown = value;
    if (opts.stripIdentifiers) {
      v = this.removeIdentifiers(v);
    }
    if (typeof v === 'object' && v !== null && typeof opts.numericBucket === 'number') {
      v = this.bucketNumbersDeep(v, opts.numericBucket);
    }
    if (typeof opts.truncatePayloadBytes === 'number') {
      v = this.truncateJson(v, opts.truncatePayloadBytes);
    }
    return v;
  }

  roundTimestamp(ts: number, roundMs: number): number {
    return Math.round(ts / roundMs) * roundMs;
  }

  private removeIdentifiers(data: unknown): unknown {
    if (data === null || typeof data !== 'object') return data;
    const blockedKeys = new Set(['id', 'deviceId', 'serial', 'mac', 'uuid', 'imei']);
    if (Array.isArray(data)) return data.map((d) => this.removeIdentifiers(d));
    const out: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(data as Record<string, unknown>)) {
      if (blockedKeys.has(k.toLowerCase())) continue;
      out[k] = this.removeIdentifiers(val);
    }
    return out;
  }

  private bucketNumbersDeep(data: unknown, step: number): unknown {
    if (typeof data === 'number') {
      return Math.round(data / step) * step;
    }
    if (Array.isArray(data)) return data.map((d) => this.bucketNumbersDeep(d, step));
    if (data && typeof data === 'object') {
      const out: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
        out[k] = this.bucketNumbersDeep(v, step);
      }
      return out;
    }
    return data;
  }

  private truncateJson(data: unknown, maxBytes: number): unknown {
    try {
      const str = JSON.stringify(data);
      if (Buffer.byteLength(str, 'utf8') <= maxBytes) return data;
      const truncated = str.slice(0, maxBytes);
      return JSON.parse(truncated + ']"'.slice(0, 0));
    } catch {
      // Fallback: return a string note if JSON parse fails
      return typeof data === 'string' ? data.slice(0, Math.max(0, maxBytes)) : '[truncated]';
    }
  }
}

