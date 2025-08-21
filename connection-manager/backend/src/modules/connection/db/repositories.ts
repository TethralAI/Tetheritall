import { Inject, Injectable, Optional } from '@nestjs/common';
import { Repository } from 'typeorm';
import { EventEntity } from './entities/event.entity.js';
import { CommandLogEntity } from './entities/command_log.entity.js';
import { PrivacyDecisionLogEntity } from './entities/privacy_decision_log.entity.js';

@Injectable()
export class OptionalRepos {
  constructor(
    @Optional() @Inject('EVENT_REPO') public readonly eventRepo?: Repository<EventEntity>,
    @Optional() @Inject('COMMAND_REPO') public readonly commandRepo?: Repository<CommandLogEntity>,
    @Optional() @Inject('PRIVACY_REPO') public readonly privacyRepo?: Repository<PrivacyDecisionLogEntity>,
  ) {}

  get ormEnabled(): boolean {
    return !!(this.eventRepo && this.commandRepo && this.privacyRepo);
  }
}

