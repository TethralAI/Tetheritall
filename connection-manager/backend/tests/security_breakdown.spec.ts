import { Test } from '@nestjs/testing';
import { HealthMonitor } from '../src/modules/connection/health/health-monitor.js';
import { ObserveModule } from '../src/modules/connection/observe/observe.module.js';
import { EventBus } from '../src/modules/connection/observe/event-bus.js';

describe('Security breakdown detection', () => {
  it('emits breakdown signal on heartbeat gap', async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [ObserveModule],
      providers: [HealthMonitor],
    }).compile();

    const bus = moduleRef.get(EventBus);
    const monitor = moduleRef.get(HealthMonitor);

    let signaled = false;
    bus.on('sec.signal.breakdown', () => {
      signaled = true;
    });

    monitor.recordHeartbeat({ deviceId: 'dev-1', ts: Date.now() - 2000 });
    monitor.recordHeartbeat({ deviceId: 'dev-1', ts: Date.now(), packetLossPct: 60 });

    expect(signaled).toBe(true);
  });
});

