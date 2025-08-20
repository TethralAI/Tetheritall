import { Test } from '@nestjs/testing';
import { EgressGuard } from '../src/modules/connection/privacy/egress-guard.service.js';
import { PrivacyModule } from '../src/modules/connection/privacy/privacy.module.js';

describe('Privacy filters and egress guard', () => {
  it('denies export by default and returns minimized event', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [PrivacyModule] }).compile();

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

