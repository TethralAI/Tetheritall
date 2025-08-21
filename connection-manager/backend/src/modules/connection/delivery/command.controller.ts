import { Body, Controller, HttpException, HttpStatus, Post } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import { PriorityQueueService, Priority } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';

class CommandDto {
  capability!: string;
  params!: unknown;
  priority!: Priority;
  idempotencyKey!: string;
  deadline?: number;
}

@Controller('/v1/devices')
export class CommandController {
  constructor(private readonly pq: PriorityQueueService, private readonly idem: IdempotencyService) {}

  @Post('/:id/command')
  async enqueue(@Body() body: CommandDto): Promise<{ commandId: string }> {
    // In a real controller, :id param would be used from route param
    const deviceId = (body as any).deviceId ?? 'unknown';
    if (!this.idem.checkAndRecord(deviceId, body.idempotencyKey)) {
      throw new HttpException('Duplicate command', HttpStatus.CONFLICT);
    }
    const commandId = uuidv4();
    this.pq.enqueue({
      commandId,
      deviceId,
      capability: body.capability,
      params: body.params,
      priority: body.priority,
      deadline: body.deadline,
      idempotencyKey: body.idempotencyKey,
      enqueuedAt: Date.now(),
    });
    return { commandId };
  }
}

