export interface ShadowEntry {
  version: number;
  reported: Record<string, unknown>;
  updatedAt: number;
}

export interface ShadowStore {
  get(deviceId: string): Promise<ShadowEntry | undefined>;
  applyUpdate(deviceId: string, version: number, patch: Record<string, unknown>): Promise<ShadowEntry>;
}

