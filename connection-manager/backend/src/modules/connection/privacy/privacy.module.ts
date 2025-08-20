import { Module } from '@nestjs/common';
import { PrivacyClassifier } from './privacy-classifier.service.js';
import { ConsentCache } from './consent-cache.service.js';
import { EgressGuard } from './egress-guard.service.js';
import { MinimizationService } from './minimization/minimization.service.js';
import { ObserveModule } from '../observe/observe.module.js';
import { LocalOnlyModeService } from './local-only.service.js';

@Module({
  imports: [ObserveModule],
  providers: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService, LocalOnlyModeService],
  exports: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService, LocalOnlyModeService],
})
export class PrivacyModule {}

