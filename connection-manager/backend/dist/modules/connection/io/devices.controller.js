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
import { Body, Controller, Get, Inject, Param, Post, Query } from '@nestjs/common';
import { DeviceShadowService } from '../shadow/device-shadow.service.js';
import { DEVICE_STORE } from '../db/store.tokens.js';
let DevicesController = class DevicesController {
    shadow;
    devices;
    constructor(shadow, devices) {
        this.shadow = shadow;
        this.devices = devices;
    }
    create(body) {
        const id = body.deviceId;
        return this.devices.create(id, body.capabilities ?? [], body.status ?? 'offline');
    }
    list(capability, status) {
        return this.devices.list({ capability: capability ?? undefined, status: status ?? undefined }).then((items) => ({ items }));
    }
    shadowGet(id) {
        return this.shadow.get(id).then((s) => s ?? { version: 0, reported: {}, updatedAt: 0 });
    }
    async shadowUpdate(id, body) {
        const next = await this.shadow.applyUpdate(id, body.version, body.patch);
        return next;
    }
};
__decorate([
    Post(''),
    __param(0, Body()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", void 0)
], DevicesController.prototype, "create", null);
__decorate([
    Get(''),
    __param(0, Query('capability')),
    __param(1, Query('status')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, String]),
    __metadata("design:returntype", void 0)
], DevicesController.prototype, "list", null);
__decorate([
    Get('/:id/shadow'),
    __param(0, Param('id')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", void 0)
], DevicesController.prototype, "shadowGet", null);
__decorate([
    Post('/:id/shadow'),
    __param(0, Param('id')),
    __param(1, Body()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Promise)
], DevicesController.prototype, "shadowUpdate", null);
DevicesController = __decorate([
    Controller('/v1/devices'),
    __param(1, Inject(DEVICE_STORE)),
    __metadata("design:paramtypes", [DeviceShadowService, Object])
], DevicesController);
export { DevicesController };
//# sourceMappingURL=devices.controller.js.map