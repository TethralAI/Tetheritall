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
import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
let CommissioningController = class CommissioningController {
    sessions = new Map();
    start(_body) {
        const id = uuidv4();
        this.sessions.set(id, { id, status: 'pending', createdAt: Date.now() });
        return { id };
    }
    status(id) {
        const s = this.sessions.get(id);
        if (!s)
            return { id, status: 'failed' };
        if (Date.now() - s.createdAt > 100)
            s.status = 'success';
        return { id, status: s.status };
    }
};
__decorate([
    Post('/start'),
    __param(0, Body()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", void 0)
], CommissioningController.prototype, "start", null);
__decorate([
    Get('/:id/status'),
    __param(0, Param('id')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String]),
    __metadata("design:returntype", void 0)
], CommissioningController.prototype, "status", null);
CommissioningController = __decorate([
    Controller('/v1/connection/commission')
], CommissioningController);
export { CommissioningController };
//# sourceMappingURL=commissioning.controller.js.map