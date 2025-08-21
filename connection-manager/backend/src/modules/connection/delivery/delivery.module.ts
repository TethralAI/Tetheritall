import { Module } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';
import { CommandController } from './command.controller.js';
import { CommandWorker } from './command.worker.js';
import { ObserveModule } from '../observe/observe.module.js';

@Module({
  imports: [ObserveModule],
  providers: [PriorityQueueService, IdempotencyService, CommandWorker],
  controllers: [CommandController],
  exports: [PriorityQueueService, IdempotencyService],
})
export class DeliveryModule {}

