var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { PrivacyModule } from './privacy/privacy.module.js';
import { IoModule } from './io/io.module.js';
import { ShadowModule } from './shadow/shadow.module.js';
import { DeliveryModule } from './delivery/delivery.module.js';
let ConnectionModule = class ConnectionModule {
};
ConnectionModule = __decorate([
    Module({
        imports: [PrivacyModule, IoModule, ShadowModule, DeliveryModule],
    })
], ConnectionModule);
export { ConnectionModule };
//# sourceMappingURL=connection.module.js.map