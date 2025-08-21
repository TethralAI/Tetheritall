import { Test } from '@nestjs/testing';
import { DeliveryModule } from '../src/modules/connection/delivery/delivery.module.js';
import { PriorityQueueService } from '../src/modules/connection/delivery/priority-queue.service.js';
import { IdempotencyService } from '../src/modules/connection/delivery/idempotency.service.js';

describe('Command delivery basics', () => {
  it('enforces idempotency and priority ordering', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [DeliveryModule] }).compile();
    const pq = moduleRef.get(PriorityQueueService);
    const idem = moduleRef.get(IdempotencyService);

    const deviceId = 'dev-1';
    expect(idem.checkAndRecord(deviceId, 'k1')).toBe(true);
    expect(idem.checkAndRecord(deviceId, 'k1')).toBe(false);

    pq.enqueue({ commandId: 'c3', deviceId, capability: 'x', params: {}, priority: 'background', deadline: undefined, idempotencyKey: 'k3', enqueuedAt: Date.now() });
    pq.enqueue({ commandId: 'c2', deviceId, capability: 'x', params: {}, priority: 'routine', deadline: undefined, idempotencyKey: 'k2', enqueuedAt: Date.now() });
    pq.enqueue({ commandId: 'c1', deviceId, capability: 'x', params: {}, priority: 'emergency', deadline: undefined, idempotencyKey: 'k1b', enqueuedAt: Date.now() });

    expect(pq.dequeue()?.commandId).toBe('c1');
    expect(pq.dequeue()?.commandId).toBe('c2');
    expect(pq.dequeue()?.commandId).toBe('c3');
  });
});

