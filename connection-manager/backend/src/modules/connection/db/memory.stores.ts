import { DeviceRecord, DeviceStore } from './device.store.js';
import { ShadowEntry, ShadowStore } from './shadow.store.js';

export class InMemoryDeviceStore implements DeviceStore {
  private devices = new Map<string, DeviceRecord>();
  async create(deviceId: string, capabilities: string[], status: 'online' | 'offline'): Promise<DeviceRecord> {
    const rec: DeviceRecord = { id: deviceId, capabilities, status, createdAt: Date.now() };
    this.devices.set(deviceId, rec);
    return rec;
  }
  async list(filter?: { capability?: string; status?: 'online' | 'offline' }): Promise<DeviceRecord[]> {
    const items = Array.from(this.devices.values()).filter((d) => {
      if (filter?.capability && !d.capabilities.includes(filter.capability)) return false;
      if (filter?.status && d.status !== filter.status) return false;
      return true;
    });
    return items;
  }
}

export class InMemoryShadowStore implements ShadowStore {
  private shadows = new Map<string, ShadowEntry>();
  async get(deviceId: string): Promise<ShadowEntry | undefined> {
    return this.shadows.get(deviceId);
  }
  async applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry> {
    const current = this.shadows.get(deviceId) ?? { version: 0, reported: {}, updatedAt: 0 };
    if (version <= current.version) return current;
    const next: ShadowEntry = { version, reported: { ...current.reported, ...patch }, updatedAt: Date.now() };
    this.shadows.set(deviceId, next);
    return next;
  }
}

