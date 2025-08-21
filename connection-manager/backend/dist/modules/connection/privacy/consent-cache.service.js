var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var ConsentCache_1;
import { Injectable, Logger } from '@nestjs/common';
let ConsentCache = ConsentCache_1 = class ConsentCache {
    logger = new Logger(ConsentCache_1.name);
    cache = new Map();
    async getConsent(deviceId) {
        const hit = this.cache.get(deviceId);
        if (hit && Date.now() < hit.expiresAt)
            return hit.decision;
        return null;
    }
    async putConsent(deviceId, decision) {
        const expiresAt = Date.now() + decision.ttlSec * 1000;
        this.cache.set(deviceId, { decision, expiresAt });
    }
    async fetchAndCache(deviceId) {
        try {
            const decision = {
                allowed: false,
                policyVersion: '0',
                reason: 'default_deny_no_policy',
                ttlSec: 60,
            };
            await this.putConsent(deviceId, decision);
            return decision;
        }
        catch (err) {
            this.logger.warn(`Consent fetch failed for ${deviceId}: ${String(err)}`);
            return { allowed: false, policyVersion: '0', reason: 'privacy_service_unavailable', ttlSec: 30 };
        }
    }
};
ConsentCache = ConsentCache_1 = __decorate([
    Injectable()
], ConsentCache);
export { ConsentCache };
//# sourceMappingURL=consent-cache.service.js.map