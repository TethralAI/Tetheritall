import { Test } from '@nestjs/testing';
import { EgressGuard } from '../src/modules/connection/privacy/egress-guard.service.js';
import { PrivacyClassifier } from '../src/modules/connection/privacy/privacy-classifier.service.js';
import { MinimizationService } from '../src/modules/connection/privacy/minimization/minimization.service.js';
import { ConsentCache } from '../src/modules/connection/privacy/consent-cache.service.js';

describe('Privacy filters and egress guard', () => {
  it('denies export by default and returns minimized event', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [EgressGuard, PrivacyClassifier, MinimizationService, ConsentCache],
    }).compile();

    const guard = moduleRef.get(EgressGuard);
    const res = await guard.evaluate({
      deviceId: 'dev-1',
      capability: 'temperature',
      value: { c: 21.37, id: 'abc', extra: 'x'.repeat(5000) },
      ts: Date.now(),
    });

    expect(res.allowed).toBe(false);
    expect(res.policyVersion).toBeDefined();
    expect(res.eventMinimized?.capability).toBe('temperature');
  });
});

