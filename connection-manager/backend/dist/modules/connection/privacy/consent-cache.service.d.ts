export interface ConsentDecision {
    allowed: boolean;
    policyVersion: string;
    reason?: string;
    ttlSec: number;
}
export declare class ConsentCache {
    private readonly logger;
    private cache;
    getConsent(deviceId: string): Promise<ConsentDecision | null>;
    putConsent(deviceId: string, decision: ConsentDecision): Promise<void>;
    fetchAndCache(deviceId: string): Promise<ConsentDecision>;
}
