import { EgressGuard } from '../privacy/egress-guard.service.js';
declare class IngestDto {
    deviceId: string;
    capability: string;
    value: unknown;
    ts: number;
}
export declare class IngestController {
    private readonly guard;
    constructor(guard: EgressGuard);
    ingest(body: IngestDto): Promise<{
        allowed: boolean;
        policyVersion: string;
        reason: string | undefined;
        event: import("../privacy/privacy-classifier.service.js").ClassifiedEvent<unknown> | undefined;
    }>;
}
export {};
