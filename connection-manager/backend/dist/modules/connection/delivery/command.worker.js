var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var CommandWorker_1;
import { Injectable, Logger } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { EventBus } from '../observe/event-bus.js';
let CommandWorker = CommandWorker_1 = class CommandWorker {
    pq;
    bus;
    logger = new Logger(CommandWorker_1.name);
    running = false;
    constructor(pq, bus) {
        this.pq = pq;
        this.bus = bus;
    }
    start() {
        if (this.running)
            return;
        this.running = true;
        this.loop();
    }
    stop() {
        this.running = false;
    }
    async loop() {
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
                await new Promise((r) => setTimeout(r, 5));
                this.bus.emit({ type: 'conn.command.applied', deviceId: cmd.deviceId, commandId: cmd.commandId });
            }
            catch (err) {
                this.logger.warn(`Command ${cmd.commandId} failed: ${String(err)}`);
                this.bus.emit({ type: 'conn.command.failed', deviceId: cmd.deviceId, commandId: cmd.commandId });
            }
        }
    }
    onModuleInit() {
        this.start();
    }
};
CommandWorker = CommandWorker_1 = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [PriorityQueueService, EventBus])
], CommandWorker);
export { CommandWorker };
//# sourceMappingURL=command.worker.js.map