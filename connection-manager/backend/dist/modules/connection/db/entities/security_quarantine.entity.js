var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';
let SecurityQuarantineEntity = class SecurityQuarantineEntity {
    id;
    deviceId;
    mode;
    ttlSec;
    appliedAt;
    updatedAt;
};
__decorate([
    PrimaryGeneratedColumn('uuid'),
    __metadata("design:type", String)
], SecurityQuarantineEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    Index(),
    __metadata("design:type", String)
], SecurityQuarantineEntity.prototype, "deviceId", void 0);
__decorate([
    Column({ type: 'varchar', length: 16 }),
    __metadata("design:type", String)
], SecurityQuarantineEntity.prototype, "mode", void 0);
__decorate([
    Column({ type: 'int4', nullable: true }),
    __metadata("design:type", Object)
], SecurityQuarantineEntity.prototype, "ttlSec", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], SecurityQuarantineEntity.prototype, "appliedAt", void 0);
__decorate([
    UpdateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], SecurityQuarantineEntity.prototype, "updatedAt", void 0);
SecurityQuarantineEntity = __decorate([
    Entity({ name: 'security_quarantine' })
], SecurityQuarantineEntity);
export { SecurityQuarantineEntity };
//# sourceMappingURL=security_quarantine.entity.js.map