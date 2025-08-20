import { Injectable, Logger } from '@nestjs/common';

export interface ConsentDecision {
  allowed: boolean;
  policyVersion: string;
  reason?: string;
  ttlSec: number;
}

@Injectable()
export class ConsentCache {
  private readonly logger = new Logger(ConsentCache.name);
  private cache = new Map<string, { decision: ConsentDecision; expiresAt: number }>();

  async getConsent(deviceId: string): Promise<ConsentDecision | null> {
    const hit = this.cache.get(deviceId);
    if (hit && Date.now() < hit.expiresAt) return hit.decision;
    return null;
  }

  async putConsent(deviceId: string, decision: ConsentDecision): Promise<void> {
    const expiresAt = Date.now() + decision.ttlSec * 1000;
    this.cache.set(deviceId, { decision, expiresAt });
  }

  // Simulated fetch from Privacy Service. In real code, call HTTP with OIDC.
  async fetchAndCache(deviceId: string): Promise<ConsentDecision> {
    try {
      // Default-deny stance if remote not reachable
      const decision: ConsentDecision = {
        allowed: false,
        policyVersion: '0',
        reason: 'default_deny_no_policy',
        ttlSec: 60,
      };
      await this.putConsent(deviceId, decision);
      return decision;
    } catch (err) {
      this.logger.warn(`Consent fetch failed for ${deviceId}: ${String(err)}`);
      return { allowed: false, policyVersion: '0', reason: 'privacy_service_unavailable', ttlSec: 30 };
    }
  }
}

