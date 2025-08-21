import { Body, Controller, Post } from '@nestjs/common';
import { EgressGuard, IngestEvent } from '../privacy/egress-guard.service.js';
import { OptionalRepos } from '../db/repositories.js';
import { EventEntity } from '../db/entities/event.entity.js';
import { DataSource } from 'typeorm';

class IngestDto {
  deviceId!: string;
  capability!: string;
  value!: unknown;
  ts!: number;
}

@Controller('/v1/connection')
export class IngestController {
  private seqWindow = new Map<string, number>();
  private quota = new Map<string, { count: number; windowStart: number }>();
  private readonly windowMs = 10_000;
  private readonly limit = 200;

  constructor(private readonly guard: EgressGuard, private readonly repos: OptionalRepos) {}

  @Post('/ingest')
  async ingest(@Body() body: IngestDto) {
    // quotas
    const now = Date.now();
    const q = this.quota.get(body.deviceId) ?? { count: 0, windowStart: now };
    if (now - q.windowStart > this.windowMs) { q.count = 0; q.windowStart = now; }
    q.count++;
    this.quota.set(body.deviceId, q);
    if (q.count > this.limit) return { allowed: false, reason: 'rate_limited' };

    // sequencing
    const lastSeq = this.seqWindow.get(body.deviceId) ?? -1;
    const seq = typeof (body as any).seq === 'number' ? (body as any).seq : lastSeq + 1;
    if (seq <= lastSeq) {
      // drop as replay/dup
      return { allowed: false, reason: 'sequence_regression' };
    }
    this.seqWindow.set(body.deviceId, seq);

    const res = await this.guard.evaluate(body as IngestEvent);
    const response = {
      allowed: res.allowed,
      policyVersion: res.policyVersion,
      reason: res.reason,
      event: res.eventMinimized,
    };
    // persist event if allowed and ORM enabled
    if (this.repos.ormEnabled && res.allowed && res.eventMinimized) {
      const repo = this.repos.eventRepo!;
      const event = repo.create({
        deviceId: body.deviceId,
        capability: res.eventMinimized.capability,
        dataClass: res.eventMinimized.dataClass,
        purpose: res.eventMinimized.purpose,
        value: res.eventMinimized.value as any,
        policyVersion: res.policyVersion,
        seq,
      });
      await repo.save(event);
    }
    return response;
  }
}

