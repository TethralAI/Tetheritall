import { EgressGuard } from '../privacy/egress-guard.service.js';
import { OptionalRepos } from '../db/repositories.js';
declare class IngestDto {
    deviceId: string;
    capability: string;
    value: unknown;
    ts: number;
}
export declare class IngestController {
    private readonly guard;
    private readonly repos;
    private seqWindow;
    private quota;
    private readonly windowMs;
    private readonly limit;
    constructor(guard: EgressGuard, repos: OptionalRepos);
    ingest(body: IngestDto): Promise<{
        allowed: boolean;
        policyVersion: string;
        reason: string | undefined;
        event: import("../privacy/privacy-classifier.service.js").ClassifiedEvent<unknown> | undefined;
    } | {
        allowed: boolean;
        reason: string;
    }>;
}
export {};
