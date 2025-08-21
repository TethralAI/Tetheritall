import { Injectable } from '@nestjs/common';

export type DataClass = 'telemetry' | 'state' | 'diagnostic' | 'identifier' | 'location';
export type Purpose = 'automation' | 'troubleshooting' | 'analytics';

export interface ClassifiedEvent<T = unknown> {
  capability: string;
  dataClass: DataClass;
  purpose: Purpose;
  value: T;
}

@Injectable()
export class PrivacyClassifier {
  classify<T = unknown>(capability: string, value: T): ClassifiedEvent<T> {
    const lower = capability.toLowerCase();
    let dataClass: DataClass = 'telemetry';
    if (lower.includes('id') || lower.includes('mac') || lower.includes('serial')) dataClass = 'identifier';
    else if (lower.includes('gps') || lower.includes('geo') || lower.includes('location')) dataClass = 'location';
    else if (lower.includes('state') || lower.includes('mode')) dataClass = 'state';
    else if (lower.includes('diag') || lower.includes('health')) dataClass = 'diagnostic';

    const purpose: Purpose = lower.includes('health') || lower.includes('diag') ? 'troubleshooting' : 'automation';
    return { capability, dataClass, purpose, value };
  }
}

