import { Injectable } from '@nestjs/common';
import { ConsentCache, ConsentDecision } from './consent-cache.service.js';
import { PrivacyClassifier, ClassifiedEvent } from './privacy-classifier.service.js';
import { MinimizationService, MinimizationOptions } from './minimization/minimization.service.js';
import { EventBus } from '../observe/event-bus.js';
import { LocalOnlyModeService } from './local-only.service.js';

export interface IngestEvent<T = unknown> {
  deviceId: string;
  capability: string;
  value: T;
  ts: number;
}

export interface GuardResult {
  allowed: boolean;
  policyVersion: string;
  reason?: string;
  eventMinimized?: ClassifiedEvent;
}

@Injectable()
export class EgressGuard {
  constructor(
    private readonly cache: ConsentCache,
    private readonly classifier: PrivacyClassifier,
    private readonly minimizer: MinimizationService,
    private readonly bus: EventBus,
    private readonly localOnly: LocalOnlyModeService,
  ) {}

  async evaluate(event: IngestEvent): Promise<GuardResult> {
    const classified = this.classifier.classify(event.capability, event.value);
    const minimization: MinimizationOptions = {
      roundTimestampMs: 1000,
      numericBucket: classified.dataClass === 'telemetry' ? 0.5 : undefined,
      stripIdentifiers: classified.dataClass === 'identifier' || classified.dataClass === 'location',
      truncatePayloadBytes: 2 * 1024,
    };

    const minimizedValue = this.minimizer.apply(classified.value, minimization);
    const minimizedEvent: ClassifiedEvent = { ...classified, value: minimizedValue };

    let consent: ConsentDecision | null = await this.cache.getConsent(event.deviceId);
    if (!consent) consent = await this.cache.fetchAndCache(event.deviceId);

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
}

