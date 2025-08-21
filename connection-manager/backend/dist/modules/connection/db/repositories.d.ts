import { Repository } from 'typeorm';
import { EventEntity } from './entities/event.entity.js';
import { CommandLogEntity } from './entities/command_log.entity.js';
import { PrivacyDecisionLogEntity } from './entities/privacy_decision_log.entity.js';
export declare class OptionalRepos {
    readonly eventRepo?: Repository<EventEntity> | undefined;
    readonly commandRepo?: Repository<CommandLogEntity> | undefined;
    readonly privacyRepo?: Repository<PrivacyDecisionLogEntity> | undefined;
    constructor(eventRepo?: Repository<EventEntity> | undefined, commandRepo?: Repository<CommandLogEntity> | undefined, privacyRepo?: Repository<PrivacyDecisionLogEntity> | undefined);
    get ormEnabled(): boolean;
}
