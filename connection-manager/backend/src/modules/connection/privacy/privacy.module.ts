import { Module } from '@nestjs/common';
import { PrivacyClassifier } from './privacy-classifier.service.js';
import { ConsentCache } from './consent-cache.service.js';
import { EgressGuard } from './egress-guard.service.js';
import { MinimizationService } from './minimization/minimization.service.js';

@Module({
  providers: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService],
  exports: [PrivacyClassifier, ConsentCache, EgressGuard, MinimizationService],
})
export class PrivacyModule {}

