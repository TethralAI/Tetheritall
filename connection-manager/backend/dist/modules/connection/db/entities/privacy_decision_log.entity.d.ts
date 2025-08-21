export declare class PrivacyDecisionLogEntity {
    id: string;
    deviceId: string;
    allowed: boolean;
    policyVersion: string;
    reason: string | null;
    ts: Date;
}
