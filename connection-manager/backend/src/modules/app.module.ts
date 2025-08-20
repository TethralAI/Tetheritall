import { Module } from '@nestjs/common';
import { ConnectionModule } from './connection/connection.module.js';

@Module({
  imports: [ConnectionModule],
})
export class AppModule {}

