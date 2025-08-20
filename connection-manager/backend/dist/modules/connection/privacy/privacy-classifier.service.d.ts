export type DataClass = 'telemetry' | 'state' | 'diagnostic' | 'identifier' | 'location';
export type Purpose = 'automation' | 'troubleshooting' | 'analytics';
export interface ClassifiedEvent<T = unknown> {
    capability: string;
    dataClass: DataClass;
    purpose: Purpose;
    value: T;
}
export declare class PrivacyClassifier {
    classify<T = unknown>(capability: string, value: T): ClassifiedEvent<T>;
}
