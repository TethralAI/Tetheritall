export interface MinimizationOptions {
    roundTimestampMs?: number;
    numericBucket?: number;
    stripIdentifiers?: boolean;
    truncatePayloadBytes?: number;
}
export declare class MinimizationService {
    apply<T = unknown>(value: T, opts: MinimizationOptions): unknown;
    roundTimestamp(ts: number, roundMs: number): number;
    private removeIdentifiers;
    private bucketNumbersDeep;
    private truncateJson;
}
