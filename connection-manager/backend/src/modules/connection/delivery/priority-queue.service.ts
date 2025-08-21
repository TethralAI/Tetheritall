import { Injectable } from '@nestjs/common';

export type Priority = 'emergency' | 'routine' | 'background';

export interface EnqueuedCommand {
  commandId: string;
  deviceId: string;
  capability: string;
  params: unknown;
  priority: Priority;
  deadline?: number;
  idempotencyKey: string;
  enqueuedAt: number;
}

@Injectable()
export class PriorityQueueService {
  private queues: Record<Priority, EnqueuedCommand[]> = {
    emergency: [],
    routine: [],
    background: [],
  };

  enqueue(cmd: EnqueuedCommand): void {
    this.queues[cmd.priority].push(cmd);
  }

  dequeue(): EnqueuedCommand | undefined {
    return this.queues.emergency.shift() ?? this.queues.routine.shift() ?? this.queues.background.shift();
  }

  size(): number {
    return this.queues.emergency.length + this.queues.routine.length + this.queues.background.length;
  }
}

