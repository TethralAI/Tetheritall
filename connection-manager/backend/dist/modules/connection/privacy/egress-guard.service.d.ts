import { ConsentCache } from './consent-cache.service.js';
import { PrivacyClassifier, ClassifiedEvent } from './privacy-classifier.service.js';
import { MinimizationService } from './minimization/minimization.service.js';
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
export declare class EgressGuard {
    private readonly cache;
    private readonly classifier;
    private readonly minimizer;
    private readonly bus;
    private readonly localOnly;
    constructor(cache: ConsentCache, classifier: PrivacyClassifier, minimizer: MinimizationService, bus: EventBus, localOnly: LocalOnlyModeService);
    evaluate(event: IngestEvent): Promise<GuardResult>;
}
