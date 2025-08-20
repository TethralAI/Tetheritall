import { Body, Controller, Post } from '@nestjs/common';
import { EgressGuard, IngestEvent } from '../privacy/egress-guard.service.js';

class IngestDto {
  deviceId!: string;
  capability!: string;
  value!: unknown;
  ts!: number;
}

@Controller('/v1/connection')
export class IngestController {
  constructor(private readonly guard: EgressGuard) {}

  @Post('/ingest')
  async ingest(@Body() body: IngestDto) {
    const res = await this.guard.evaluate(body as IngestEvent);
    return {
      allowed: res.allowed,
      policyVersion: res.policyVersion,
      reason: res.reason,
      event: res.eventMinimized,
    };
  }
}

