import { DataSource } from 'typeorm';
import AppDataSource from '../ormconfig.js';

const DB_URL = process.env.DB_URL;

(DB_URL ? describe : describe.skip)('DB E2E CRUD', () => {
  let ds: DataSource;
  beforeAll(async () => {
    ds = await AppDataSource.initialize();
    await ds.runMigrations();
  });
  afterAll(async () => {
    await ds.destroy();
  });

  it('device CRUD', async () => {
    await ds.query(`INSERT INTO device (id,status) VALUES ('dev-e2e','online')`);
    const rows1 = await ds.query(`SELECT * FROM device WHERE id='dev-e2e'`);
    expect(rows1.length).toBe(1);
    await ds.query(`UPDATE device SET status='offline' WHERE id='dev-e2e'`);
    const rows2 = await ds.query(`SELECT status FROM device WHERE id='dev-e2e'`);
    expect(rows2[0].status).toBe('offline');
    await ds.query(`DELETE FROM device WHERE id='dev-e2e'`);
    const rows3 = await ds.query(`SELECT * FROM device WHERE id='dev-e2e'`);
    expect(rows3.length).toBe(0);
  });
});

