import { Repository } from 'typeorm';
import { DeviceEntity } from './entities/device.entity.js';
import { DeviceShadowEntity } from './entities/device_shadow.entity.js';
import type { DeviceRecord, DeviceStore } from './device.store.js';
import type { ShadowEntry, ShadowStore } from './shadow.store.js';

export class OrmDeviceStore implements DeviceStore {
  constructor(private readonly repo: Repository<DeviceEntity>) {}
  async create(deviceId: string, capabilities: string[], status: 'online' | 'offline'): Promise<DeviceRecord> {
    const row = this.repo.create({ id: deviceId, capabilities, status });
    const saved = await this.repo.save(row);
    return { id: saved.id, capabilities: saved.capabilities, status: saved.status, createdAt: saved.createdAt.getTime() };
  }
  async list(filter?: { capability?: string; status?: 'online' | 'offline' }): Promise<DeviceRecord[]> {
    const qb = this.repo.createQueryBuilder('d');
    if (filter?.status) qb.andWhere('d.status = :s', { s: filter.status });
    // JSONB array contains check
    if (filter?.capability) qb.andWhere(`d.capabilities::jsonb ? :cap`, { cap: filter.capability });
    const rows = await qb.getMany();
    return rows.map((r) => ({ id: r.id, capabilities: r.capabilities, status: r.status, createdAt: r.createdAt.getTime() }));
  }
}

export class OrmShadowStore implements ShadowStore {
  constructor(private readonly repo: Repository<DeviceShadowEntity>) {}
  async get(deviceId: string): Promise<ShadowEntry | undefined> {
    const row = await this.repo.findOne({ where: { deviceId } });
    if (!row) return undefined;
    return { version: row.version, reported: row.reported, updatedAt: row.updatedAt.getTime() };
  }
  async applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry> {
    const existing = await this.repo.findOne({ where: { deviceId } });
    if (existing && version <= existing.version) return { version: existing.version, reported: existing.reported, updatedAt: existing.updatedAt.getTime() };
    const reported = { ...(existing?.reported ?? {}), ...patch };
    const row = this.repo.create({ deviceId, version, reported });
    await this.repo.save(row);
    const final = await this.repo.findOneOrFail({ where: { deviceId } });
    return { version: final.version, reported: final.reported, updatedAt: final.updatedAt.getTime() };
  }
}

