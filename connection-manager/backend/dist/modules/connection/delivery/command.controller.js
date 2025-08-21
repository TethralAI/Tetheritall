var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { Body, Controller, HttpException, HttpStatus, Post } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import { PriorityQueueService } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';
class CommandDto {
    capability;
    params;
    priority;
    idempotencyKey;
    deadline;
}
let CommandController = class CommandController {
    pq;
    idem;
    constructor(pq, idem) {
        this.pq = pq;
        this.idem = idem;
    }
    async enqueue(body) {
        const deviceId = body.deviceId ?? 'unknown';
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
};
__decorate([
    Post('/:id/command'),
    __param(0, Body()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [CommandDto]),
    __metadata("design:returntype", Promise)
], CommandController.prototype, "enqueue", null);
CommandController = __decorate([
    Controller('/v1/devices'),
    __metadata("design:paramtypes", [PriorityQueueService, IdempotencyService])
], CommandController);
export { CommandController };
//# sourceMappingURL=command.controller.js.map