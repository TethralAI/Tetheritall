var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable } from '@nestjs/common';
import { ConsentCache } from './consent-cache.service.js';
import { PrivacyClassifier } from './privacy-classifier.service.js';
import { MinimizationService } from './minimization/minimization.service.js';
import { EventBus } from '../observe/event-bus.js';
import { LocalOnlyModeService } from './local-only.service.js';
let EgressGuard = class EgressGuard {
    cache;
    classifier;
    minimizer;
    bus;
    localOnly;
    constructor(cache, classifier, minimizer, bus, localOnly) {
        this.cache = cache;
        this.classifier = classifier;
        this.minimizer = minimizer;
        this.bus = bus;
        this.localOnly = localOnly;
    }
    async evaluate(event) {
        const classified = this.classifier.classify(event.capability, event.value);
        const minimization = {
            roundTimestampMs: 1000,
            numericBucket: classified.dataClass === 'telemetry' ? 0.5 : undefined,
            stripIdentifiers: classified.dataClass === 'identifier' || classified.dataClass === 'location',
            truncatePayloadBytes: 2 * 1024,
        };
        const minimizedValue = this.minimizer.apply(classified.value, minimization);
        const minimizedEvent = { ...classified, value: minimizedValue };
        let consent = await this.cache.getConsent(event.deviceId);
        if (!consent)
            consent = await this.cache.fetchAndCache(event.deviceId);
        if (this.localOnly.isEnabled()) {
            this.bus.emit({ type: 'conn.privacy.blocked', deviceId: event.deviceId, policyVersion: consent.policyVersion, reason: 'local_only_mode' });
            return { allowed: false, policyVersion: consent.policyVersion, reason: 'local_only_mode', eventMinimized: minimizedEvent };
        }
        if (!consent.allowed) {
            this.bus.emit({ type: 'conn.privacy.blocked', deviceId: event.deviceId, policyVersion: consent.policyVersion, reason: consent.reason });
            return { allowed: false, policyVersion: consent.policyVersion, reason: consent.reason ?? 'denied', eventMinimized: minimizedEvent };
        }
        this.bus.emit({ type: 'conn.privacy.allowed', deviceId: event.deviceId, policyVersion: consent.policyVersion });
        return { allowed: true, policyVersion: consent.policyVersion, eventMinimized: minimizedEvent };
    }
};
EgressGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [ConsentCache,
        PrivacyClassifier,
        MinimizationService,
        EventBus,
        LocalOnlyModeService])
], EgressGuard);
export { EgressGuard };
//# sourceMappingURL=egress-guard.service.js.map