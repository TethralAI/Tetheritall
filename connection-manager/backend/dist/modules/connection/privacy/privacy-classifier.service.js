var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
let PrivacyClassifier = class PrivacyClassifier {
    classify(capability, value) {
        const lower = capability.toLowerCase();
        let dataClass = 'telemetry';
        if (lower.includes('id') || lower.includes('mac') || lower.includes('serial'))
            dataClass = 'identifier';
        else if (lower.includes('gps') || lower.includes('geo') || lower.includes('location'))
            dataClass = 'location';
        else if (lower.includes('state') || lower.includes('mode'))
            dataClass = 'state';
        else if (lower.includes('diag') || lower.includes('health'))
            dataClass = 'diagnostic';
        const purpose = lower.includes('health') || lower.includes('diag') ? 'troubleshooting' : 'automation';
        return { capability, dataClass, purpose, value };
    }
};
PrivacyClassifier = __decorate([
    Injectable()
], PrivacyClassifier);
export { PrivacyClassifier };
//# sourceMappingURL=privacy-classifier.service.js.map