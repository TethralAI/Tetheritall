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
import { Body, Controller, Post } from '@nestjs/common';
import { EgressGuard } from '../privacy/egress-guard.service.js';
import { OptionalRepos } from '../db/repositories.js';
class IngestDto {
    deviceId;
    capability;
    value;
    ts;
}
let IngestController = class IngestController {
    guard;
    repos;
    seqWindow = new Map();
    quota = new Map();
    windowMs = 10_000;
    limit = 200;
    constructor(guard, repos) {
        this.guard = guard;
        this.repos = repos;
    }
    async ingest(body) {
        const now = Date.now();
        const q = this.quota.get(body.deviceId) ?? { count: 0, windowStart: now };
        if (now - q.windowStart > this.windowMs) {
            q.count = 0;
            q.windowStart = now;
        }
        q.count++;
        this.quota.set(body.deviceId, q);
        if (q.count > this.limit)
            return { allowed: false, reason: 'rate_limited' };
        const lastSeq = this.seqWindow.get(body.deviceId) ?? -1;
        const seq = typeof body.seq === 'number' ? body.seq : lastSeq + 1;
        if (seq <= lastSeq) {
            return { allowed: false, reason: 'sequence_regression' };
        }
        this.seqWindow.set(body.deviceId, seq);
        const res = await this.guard.evaluate(body);
        const response = {
            allowed: res.allowed,
            policyVersion: res.policyVersion,
            reason: res.reason,
            event: res.eventMinimized,
        };
        if (this.repos.ormEnabled && res.allowed && res.eventMinimized) {
            const repo = this.repos.eventRepo;
            const event = repo.create({
                deviceId: body.deviceId,
                capability: res.eventMinimized.capability,
                dataClass: res.eventMinimized.dataClass,
                purpose: res.eventMinimized.purpose,
                value: res.eventMinimized.value,
                policyVersion: res.policyVersion,
                seq,
            });
            await repo.save(event);
        }
        return response;
    }
};
__decorate([
    Post('/ingest'),
    __param(0, Body()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [IngestDto]),
    __metadata("design:returntype", Promise)
], IngestController.prototype, "ingest", null);
IngestController = __decorate([
    Controller('/v1/connection'),
    __metadata("design:paramtypes", [EgressGuard, OptionalRepos])
], IngestController);
export { IngestController };
//# sourceMappingURL=ingest.controller.js.map