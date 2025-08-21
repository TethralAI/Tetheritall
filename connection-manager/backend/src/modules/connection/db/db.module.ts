import { Module, Provider } from '@nestjs/common';
import { DEVICE_STORE, SHADOW_STORE } from './store.tokens.js';
import { InMemoryDeviceStore, InMemoryShadowStore } from './memory.stores.js';
import { TypeOrmModule, getRepositoryToken } from '@nestjs/typeorm';
import { DeviceEntity } from './entities/device.entity.js';
import { DeviceShadowEntity } from './entities/device_shadow.entity.js';
import { CommandLogEntity } from './entities/command_log.entity.js';
import { EventEntity } from './entities/event.entity.js';
import { SecurityEventEntity } from './entities/security_event.entity.js';
import { PrivacyDecisionLogEntity } from './entities/privacy_decision_log.entity.js';
import { OrmDeviceStore, OrmShadowStore } from './typeorm.stores.js';

const ormProviders: Provider[] = [
  {
    provide: DEVICE_STORE,
    inject: [getRepositoryToken(DeviceEntity)],
    useFactory: (repo: any) => new OrmDeviceStore(repo),
  },
  {
    provide: SHADOW_STORE,
    inject: [getRepositoryToken(DeviceShadowEntity)],
    useFactory: (repo: any) => new OrmShadowStore(repo),
  },
];

@Module({
  imports: process.env.DB_URL
    ? [
        TypeOrmModule.forRoot({
          type: 'postgres',
          url: process.env.DB_URL,
          entities: [DeviceEntity, DeviceShadowEntity, CommandLogEntity, EventEntity, SecurityEventEntity, PrivacyDecisionLogEntity],
          synchronize: true,
        }),
        TypeOrmModule.forFeature([DeviceEntity, DeviceShadowEntity, CommandLogEntity, EventEntity, SecurityEventEntity, PrivacyDecisionLogEntity]),
      ]
    : [],
  providers: process.env.DB_URL
    ? ormProviders
    : [
        { provide: DEVICE_STORE, useClass: InMemoryDeviceStore },
        { provide: SHADOW_STORE, useClass: InMemoryShadowStore },
      ],
  exports: [DEVICE_STORE, SHADOW_STORE],
})
export class DbModule {}

