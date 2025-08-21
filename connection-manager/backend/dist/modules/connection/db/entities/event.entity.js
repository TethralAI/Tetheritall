var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';
let EventEntity = class EventEntity {
    id;
    deviceId;
    capability;
    dataClass;
    purpose;
    value;
    seq;
    policyVersion;
    ts;
};
__decorate([
    PrimaryGeneratedColumn('uuid'),
    __metadata("design:type", String)
], EventEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], EventEntity.prototype, "deviceId", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], EventEntity.prototype, "capability", void 0);
__decorate([
    Column({ type: 'varchar', length: 32 }),
    __metadata("design:type", String)
], EventEntity.prototype, "dataClass", void 0);
__decorate([
    Column({ type: 'varchar', length: 32 }),
    __metadata("design:type", String)
], EventEntity.prototype, "purpose", void 0);
__decorate([
    Column({ type: 'jsonb' }),
    __metadata("design:type", Object)
], EventEntity.prototype, "value", void 0);
__decorate([
    Column({ type: 'int8' }),
    Index(),
    __metadata("design:type", Number)
], EventEntity.prototype, "seq", void 0);
__decorate([
    Column({ type: 'varchar', length: 32 }),
    __metadata("design:type", String)
], EventEntity.prototype, "policyVersion", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], EventEntity.prototype, "ts", void 0);
EventEntity = __decorate([
    Entity({ name: 'event' })
], EventEntity);
export { EventEntity };
//# sourceMappingURL=event.entity.js.map