export class Init1700000000000 {
    name = 'Init1700000000000';
    async up(q) {
        await q.query(`CREATE TABLE IF NOT EXISTS device (id VARCHAR(128) PRIMARY KEY, capabilities JSONB NOT NULL DEFAULT '[]', status VARCHAR(16) NOT NULL DEFAULT 'offline', created_at TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_device_status ON device (status)`);
        await q.query(`CREATE TABLE IF NOT EXISTS device_credentials (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL, enc_blob BYTES NOT NULL, enc_alg VARCHAR(64) NOT NULL, key_ref VARCHAR(256) NOT NULL, version INT4 NOT NULL DEFAULT 1, is_active BOOL NOT NULL DEFAULT true, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), CONSTRAINT fk_dc_device FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE CASCADE)`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_dc_device ON device_credentials (device_id)`);
        await q.query(`CREATE TABLE IF NOT EXISTS device_shadow (device_id VARCHAR(128) PRIMARY KEY, version INT4 NOT NULL DEFAULT 0, reported JSONB NOT NULL DEFAULT '{}' , updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), CONSTRAINT fk_ds_device FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE CASCADE)`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_ds_version ON device_shadow (version)`);
        await q.query(`CREATE TABLE IF NOT EXISTS event (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL, capability VARCHAR(128) NOT NULL, data_class VARCHAR(32) NOT NULL, purpose VARCHAR(32) NOT NULL, value JSONB NOT NULL, seq INT8 NOT NULL, policy_version VARCHAR(32) NOT NULL, ts TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_event_device_seq ON event (device_id, seq)`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_event_ts ON event (ts)`);
        await q.query(`CREATE TABLE IF NOT EXISTS command_log (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL, capability VARCHAR(128) NOT NULL, params JSONB NOT NULL, priority VARCHAR(16) NOT NULL, deadline INT8 NULL, idempotency_key VARCHAR(128) NOT NULL, status VARCHAR(16) NOT NULL, error TEXT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE UNIQUE INDEX IF NOT EXISTS ux_cmd_device_idem ON command_log (device_id, idempotency_key)`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_cmd_status ON command_log (status)`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_cmd_device_created ON command_log (device_id, created_at DESC)`);
        await q.query(`CREATE TABLE IF NOT EXISTS privacy_decision_log (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL, allowed BOOL NOT NULL, policy_version VARCHAR(32) NOT NULL, reason VARCHAR(128) NULL, ts TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_priv_device_ts ON privacy_decision_log (device_id, ts)`);
        await q.query(`CREATE TABLE IF NOT EXISTS security_event (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL, type VARCHAR(64) NOT NULL, detail JSONB NULL, ts TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_sec_device_ts ON security_event (device_id, ts)`);
        await q.query(`CREATE TABLE IF NOT EXISTS security_quarantine (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id VARCHAR(128) NOT NULL UNIQUE, mode VARCHAR(16) NOT NULL, ttl_sec INT4 NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())`);
        await q.query(`CREATE INDEX IF NOT EXISTS idx_sq_device ON security_quarantine (device_id)`);
    }
    async down(q) {
        await q.query(`DROP TABLE IF EXISTS security_quarantine`);
        await q.query(`DROP TABLE IF EXISTS security_event`);
        await q.query(`DROP TABLE IF EXISTS privacy_decision_log`);
        await q.query(`DROP TABLE IF EXISTS command_log`);
        await q.query(`DROP TABLE IF EXISTS event`);
        await q.query(`DROP TABLE IF EXISTS device_shadow`);
        await q.query(`DROP TABLE IF EXISTS device_credentials`);
        await q.query(`DROP TABLE IF EXISTS device`);
    }
}
//# sourceMappingURL=1700000000000-Init.js.map