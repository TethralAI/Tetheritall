export class InMemoryDeviceStore {
    devices = new Map();
    async create(deviceId, capabilities, status) {
        const rec = { id: deviceId, capabilities, status, createdAt: Date.now() };
        this.devices.set(deviceId, rec);
        return rec;
    }
    async list(filter) {
        const items = Array.from(this.devices.values()).filter((d) => {
            if (filter?.capability && !d.capabilities.includes(filter.capability))
                return false;
            if (filter?.status && d.status !== filter.status)
                return false;
            return true;
        });
        return items;
    }
}
export class InMemoryShadowStore {
    shadows = new Map();
    async get(deviceId) {
        return this.shadows.get(deviceId);
    }
    async applyUpdate(deviceId, version, patch) {
        const current = this.shadows.get(deviceId) ?? { version: 0, reported: {}, updatedAt: 0 };
        if (version <= current.version)
            return current;
        const next = { version, reported: { ...current.reported, ...patch }, updatedAt: Date.now() };
        this.shadows.set(deviceId, next);
        return next;
    }
}
//# sourceMappingURL=memory.stores.js.map