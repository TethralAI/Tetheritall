import { Module } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';
import { CommandController } from './command.controller.js';

@Module({
  providers: [PriorityQueueService, IdempotencyService],
  controllers: [CommandController],
  exports: [PriorityQueueService, IdempotencyService],
})
export class DeliveryModule {}

