var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { PriorityQueueService } from './priority-queue.service.js';
import { IdempotencyService } from './idempotency.service.js';
import { CommandController } from './command.controller.js';
let DeliveryModule = class DeliveryModule {
};
DeliveryModule = __decorate([
    Module({
        providers: [PriorityQueueService, IdempotencyService],
        controllers: [CommandController],
        exports: [PriorityQueueService, IdempotencyService],
    })
], DeliveryModule);
export { DeliveryModule };
//# sourceMappingURL=delivery.module.js.map