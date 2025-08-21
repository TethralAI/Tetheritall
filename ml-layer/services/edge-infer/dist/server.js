import express from 'express';
import pino from 'pino';
import { Kafka, logLevel } from 'kafkajs';
const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const app = express();
app.use(express.json());
// Health
app.get('/health', (_req, res) => res.json({ ok: true }));
// Stub infer endpoint
app.post('/infer/anomaly', (req, res) => {
    const { features } = req.body || {};
    // Placeholder: simple score
    const score = Array.isArray(features) ? Math.min(1, features.reduce((a, b) => a + Math.abs(Number(b) || 0), 0) / 100) : 0.1;
    res.json({ score, modelVersion: 'v0', rationale: 'stub' });
});
// Kafka adapter (optional)
const kafkaUrl = process.env.KAFKA_BROKERS ? process.env.KAFKA_BROKERS.split(',') : [];
const kafka = kafkaUrl.length ? new Kafka({ brokers: kafkaUrl, logLevel: logLevel.NOTHING }) : null;
async function start() {
    const port = Number(process.env.PORT || 7070);
    app.listen(port, () => logger.info({ port }, 'edge-infer started'));
}
start().catch((err) => {
    logger.error({ err }, 'fatal');
    process.exit(1);
});
