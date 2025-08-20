var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { IngestController } from './ingest.controller.js';
import { PrivacyModule } from '../privacy/privacy.module.js';
import { EventBus } from '../observe/event-bus.js';
import { WsGateway } from './ws.gateway.js';
import { CommissioningController } from './commissioning.controller.js';
import { DevicesController } from './devices.controller.js';
import { ShadowModule } from '../shadow/shadow.module.js';
let IoModule = class IoModule {
};
IoModule = __decorate([
    Module({
        imports: [PrivacyModule, ShadowModule],
        controllers: [IngestController, CommissioningController, DevicesController],
        providers: [EventBus, WsGateway],
        exports: [EventBus],
    })
], IoModule);
export { IoModule };
//# sourceMappingURL=io.module.js.map