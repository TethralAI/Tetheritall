import { Module } from '@nestjs/common';
import { IngestController } from './ingest.controller.js';
import { PrivacyModule } from '../privacy/privacy.module.js';

@Module({
  imports: [PrivacyModule],
  controllers: [IngestController],
})
export class IoModule {}

