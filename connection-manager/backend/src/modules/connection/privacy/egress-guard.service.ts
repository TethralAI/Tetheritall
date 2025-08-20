import { Injectable } from '@nestjs/common';
import { ConsentCache, ConsentDecision } from './consent-cache.service.js';
import { PrivacyClassifier, ClassifiedEvent } from './privacy-classifier.service.js';
import { MinimizationService, MinimizationOptions } from './minimization/minimization.service.js';

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

    if (!consent.allowed) {
      return { allowed: false, policyVersion: consent.policyVersion, reason: consent.reason ?? 'denied', eventMinimized: minimizedEvent };
    }

    return { allowed: true, policyVersion: consent.policyVersion, eventMinimized: minimizedEvent };
  }
}

