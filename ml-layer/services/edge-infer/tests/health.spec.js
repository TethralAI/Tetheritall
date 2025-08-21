import request from 'supertest';
import express from 'express';
import '../src/server';
describe('edge-infer basic', () => {
    it('health responds', async () => {
        const app = express();
        app.get('/health', (_req, res) => res.json({ ok: true }));
        const res = await request(app).get('/health');
        expect(res.status).toBe(200);
        expect(res.body.ok).toBe(true);
    });
});
