var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';
let PrivacyDecisionLogEntity = class PrivacyDecisionLogEntity {
    id;
    deviceId;
    allowed;
    policyVersion;
    reason;
    ts;
};
__decorate([
    PrimaryGeneratedColumn('uuid'),
    __metadata("design:type", String)
], PrivacyDecisionLogEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], PrivacyDecisionLogEntity.prototype, "deviceId", void 0);
__decorate([
    Column({ type: 'boolean' }),
    __metadata("design:type", Boolean)
], PrivacyDecisionLogEntity.prototype, "allowed", void 0);
__decorate([
    Column({ type: 'varchar', length: 32 }),
    __metadata("design:type", String)
], PrivacyDecisionLogEntity.prototype, "policyVersion", void 0);
__decorate([
    Column({ type: 'varchar', length: 128, nullable: true }),
    __metadata("design:type", Object)
], PrivacyDecisionLogEntity.prototype, "reason", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], PrivacyDecisionLogEntity.prototype, "ts", void 0);
PrivacyDecisionLogEntity = __decorate([
    Entity({ name: 'privacy_decision_log' })
], PrivacyDecisionLogEntity);
export { PrivacyDecisionLogEntity };
//# sourceMappingURL=privacy_decision_log.entity.js.map