var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { DEVICE_STORE, SHADOW_STORE } from './store.tokens.js';
import { InMemoryDeviceStore, InMemoryShadowStore } from './memory.stores.js';
let DbModule = class DbModule {
};
DbModule = __decorate([
    Module({
        providers: [
            { provide: DEVICE_STORE, useClass: InMemoryDeviceStore },
            { provide: SHADOW_STORE, useClass: InMemoryShadowStore },
        ],
        exports: [DEVICE_STORE, SHADOW_STORE],
    })
], DbModule);
export { DbModule };
//# sourceMappingURL=db.module.js.map