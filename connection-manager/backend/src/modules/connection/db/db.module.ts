import { Module } from '@nestjs/common';
import { DEVICE_STORE, SHADOW_STORE } from './store.tokens.js';
import { InMemoryDeviceStore, InMemoryShadowStore } from './memory.stores.js';

@Module({
  providers: [
    { provide: DEVICE_STORE, useClass: InMemoryDeviceStore },
    { provide: SHADOW_STORE, useClass: InMemoryShadowStore },
  ],
  exports: [DEVICE_STORE, SHADOW_STORE],
})
export class DbModule {}

