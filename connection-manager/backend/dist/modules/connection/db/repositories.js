var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { Inject, Injectable, Optional } from '@nestjs/common';
import { Repository } from 'typeorm';
let OptionalRepos = class OptionalRepos {
    eventRepo;
    commandRepo;
    privacyRepo;
    constructor(eventRepo, commandRepo, privacyRepo) {
        this.eventRepo = eventRepo;
        this.commandRepo = commandRepo;
        this.privacyRepo = privacyRepo;
    }
    get ormEnabled() {
        return !!(this.eventRepo && this.commandRepo && this.privacyRepo);
    }
};
OptionalRepos = __decorate([
    Injectable(),
    __param(0, Optional()),
    __param(0, Inject('EVENT_REPO')),
    __param(1, Optional()),
    __param(1, Inject('COMMAND_REPO')),
    __param(2, Optional()),
    __param(2, Inject('PRIVACY_REPO')),
    __metadata("design:paramtypes", [Repository,
        Repository,
        Repository])
], OptionalRepos);
export { OptionalRepos };
//# sourceMappingURL=repositories.js.map