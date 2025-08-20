import { ConsentCache } from './consent-cache.service.js';
import { PrivacyClassifier, ClassifiedEvent } from './privacy-classifier.service.js';
import { MinimizationService } from './minimization/minimization.service.js';
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
    constructor(cache: ConsentCache, classifier: PrivacyClassifier, minimizer: MinimizationService);
    evaluate(event: IngestEvent): Promise<GuardResult>;
}
