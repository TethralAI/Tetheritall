import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AppModule } from '../src/modules/app.module.js';
import { io, Socket } from 'socket.io-client';
import jwt from 'jsonwebtoken';

describe('WS E2E - shadow update broadcast', () => {
  let app: INestApplication;
  let serverUrl: string;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
    const server = await app.listen(0);
    const address = server.address();
    const port = typeof address === 'string' ? 80 : address?.port ?? 3000;
    serverUrl = `http://127.0.0.1:${port}`;
  });

  afterAll(async () => {
    await app.close();
  });

  it('broadcasts conn.shadow.updated to device room', async () => {
    const token = jwt.sign({ sub: 'user-1' }, process.env.JWT_SECRET || 'dev-secret');
    const client: Socket = io(`${serverUrl}/v1/stream`, { auth: { token }, transports: ['websocket'] });
    await new Promise<void>((resolve) => client.on('connect', () => resolve()));
    client.emit('subscribe', { deviceId: 'dev-123' });

    const recv = new Promise((resolve) => client.on('conn.shadow.updated', resolve));

    // Trigger a shadow update via HTTP API
    const res = await fetch(`${serverUrl}/v1/devices/dev-123/shadow`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ version: 1, patch: { temperature: 22 } }),
    });
    expect(res.status).toBeLessThan(400);
    const evt: any = await Promise.race([
      recv,
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout waiting for event')), 2000)),
    ]);

    expect(evt).toBeTruthy();
    client.close();
  });
});

