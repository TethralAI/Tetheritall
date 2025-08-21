var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { PrivacyClassifier } from './privacy-classifier.service.js';
import { ConsentCache } from './consent-cache.service.js';
import { EgressGuard } from './egress-guard.service.js';
import { MinimizationService } from './minimization/minimization.service.js';
import { ObserveModule } from '../observe/observe.module.js';
import { DbModule } from '../db/db.module.js';
import { LocalOnlyModeService } from './local-only.service.js';
let PrivacyModule = class PrivacyModule {
};
PrivacyModule = __decorate([
    Module({
        imports: [ObserveModule, DbModule],
        providers: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService, LocalOnlyModeService],
        exports: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService, LocalOnlyModeService],
    })
], PrivacyModule);
export { PrivacyModule };
//# sourceMappingURL=privacy.module.js.map