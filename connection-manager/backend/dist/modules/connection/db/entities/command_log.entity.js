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
let CommandLogEntity = class CommandLogEntity {
    id;
    deviceId;
    capability;
    params;
    priority;
    deadline;
    idempotencyKey;
    status;
    error;
    createdAt;
    updatedAt;
};
__decorate([
    PrimaryGeneratedColumn('uuid'),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "deviceId", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "capability", void 0);
__decorate([
    Column({ type: 'jsonb' }),
    __metadata("design:type", Object)
], CommandLogEntity.prototype, "params", void 0);
__decorate([
    Column({ type: 'varchar', length: 16 }),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "priority", void 0);
__decorate([
    Column({ type: 'bigint', nullable: true }),
    __metadata("design:type", Object)
], CommandLogEntity.prototype, "deadline", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    Index(),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "idempotencyKey", void 0);
__decorate([
    Column({ type: 'varchar', length: 16 }),
    Index(),
    __metadata("design:type", String)
], CommandLogEntity.prototype, "status", void 0);
__decorate([
    Column({ type: 'text', nullable: true }),
    __metadata("design:type", Object)
], CommandLogEntity.prototype, "error", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], CommandLogEntity.prototype, "createdAt", void 0);
__decorate([
    UpdateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], CommandLogEntity.prototype, "updatedAt", void 0);
CommandLogEntity = __decorate([
    Entity({ name: 'command_log' })
], CommandLogEntity);
export { CommandLogEntity };
//# sourceMappingURL=command_log.entity.js.map