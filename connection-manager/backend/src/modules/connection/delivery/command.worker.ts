import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { EventBus } from '../observe/event-bus.js';

@Injectable()
export class CommandWorker implements OnModuleInit {
	private readonly logger = new Logger(CommandWorker.name);
	private running = false;

	constructor(private readonly pq: PriorityQueueService, private readonly bus: EventBus) {}

	start(): void {
		if (this.running) return;
		this.running = true;
		this.loop();
	}

	stop(): void {
		this.running = false;
	}

	private async loop(): Promise<void> {
		while (this.running) {
			const cmd = this.pq.dequeue();
			if (!cmd) {
				await new Promise((r) => setTimeout(r, 25));
				continue;
			}
			if (cmd.deadline && Date.now() > cmd.deadline) {
				this.bus.emit({ type: 'conn.command.expired', deviceId: cmd.deviceId, commandId: cmd.commandId });
				continue;
			}
			try {
				this.bus.emit({ type: 'conn.command.delivering', deviceId: cmd.deviceId, commandId: cmd.commandId });
				// TODO: send via adapter based on capability
				await new Promise((r) => setTimeout(r, 5));
				this.bus.emit({ type: 'conn.command.applied', deviceId: cmd.deviceId, commandId: cmd.commandId });
			} catch (err) {
				this.logger.warn(`Command ${cmd.commandId} failed: ${String(err)}`);
				this.bus.emit({ type: 'conn.command.failed', deviceId: cmd.deviceId, commandId: cmd.commandId });
			}
		}
	}

	onModuleInit(): void {
		this.start();
	}
}