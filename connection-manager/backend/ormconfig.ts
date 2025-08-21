import { DataSource } from 'typeorm';
import { DeviceEntity } from './src/modules/connection/db/entities/device.entity.js';
import { DeviceShadowEntity } from './src/modules/connection/db/entities/device_shadow.entity.js';
import { CommandLogEntity } from './src/modules/connection/db/entities/command_log.entity.js';
import { EventEntity } from './src/modules/connection/db/entities/event.entity.js';
import { SecurityEventEntity } from './src/modules/connection/db/entities/security_event.entity.js';
import { PrivacyDecisionLogEntity } from './src/modules/connection/db/entities/privacy_decision_log.entity.js';
import { DeviceCredentialsEntity } from './src/modules/connection/db/entities/device_credentials.entity.js';
import { SecurityQuarantineEntity } from './src/modules/connection/db/entities/security_quarantine.entity.js';

const migrationsPath = process.env.NODE_ENV === 'test' ? 'src/migrations/*.ts' : 'dist/migrations/*.js';

export default new DataSource({
  type: 'postgres',
  url: process.env.DB_URL,
  entities: [
    DeviceEntity,
    DeviceShadowEntity,
    CommandLogEntity,
    EventEntity,
    SecurityEventEntity,
    PrivacyDecisionLogEntity,
    DeviceCredentialsEntity,
    SecurityQuarantineEntity,
  ],
  migrations: [migrationsPath],
  synchronize: false,
});

